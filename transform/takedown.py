# Takedown list: athletes who asked to be removed from the site.
#
# The list lives in data/takedown_list.txt. This repository is public, so the file holds a SHA-256
# hash of each normalized name rather than the name itself: a public list of "people who asked to be
# removed" would defeat the point. (A hash only hides a name from someone who doesn't already have a
# guess for it; it stops casual reading, not a determined search.)
#
# The list is applied at every step that could put a name back on the site:
#   - scraper/meet_scraper.py skips listed athletes when it appends new rows,
#   - transform/meet_clean.py drops them, so CLEANED/FEATURES never contain them,
#   - transform/load_to_supabase.py drops them again before loading (in case it is run on an old
#     local FEATURES file) and deletes them from the one-run-behind backup table,
#   - `add` and `purge` below remove them from the CSVs tracked in git.
#
# Names are matched on the same key the website uses (app/api/index.py: trimmed, whitespace
# collapsed, lowercased), so "Jane  Doe" and "jane doe" are the same athlete. A spelling that differs
# in any other way is a different name and needs its own entry.
#
# Usage (from the repo root):
#     python transform/takedown.py add "Jane Doe" ["Other Name" ...]   # list them + purge the CSVs
#     python transform/takedown.py check "Jane Doe"                    # listed? rows left in the CSVs?
#     python transform/takedown.py purge                               # re-apply the list to the CSVs
# Then commit data/takedown_list.txt and the CSVs and push to main: that triggers the GitHub workflow,
# which rebuilds the site's table without them.

import csv
import hashlib
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
LIST_PATH = os.path.join(DATA_DIR, "takedown_list.txt")
# CSVs tracked in git (so published on GitHub) that hold athlete names.
TRACKED_CSVS = [
    os.path.join(DATA_DIR, "meet_results.csv"),
    os.path.join(DATA_DIR, "meet_results_CLEANED.csv"),
]

LIST_HEADER = """\
# Athletes removed at their request. Manage this file with transform/takedown.py, not by hand.
# One line per name: the SHA-256 hash of the normalized name (trimmed, whitespace collapsed,
# lowercased), so the names themselves aren't published in this public repository.
"""


def name_key(name) -> str:
    """The website's athlete key (must match normalize() in app/api/index.py)."""
    return re.sub(r"\s+", " ", str(name)).strip().lower()


def name_hash(name) -> str:
    return hashlib.sha256(name_key(name).encode("utf-8")).hexdigest()


def load_hashes(path=None) -> set:
    """The listed hashes. A missing file means nobody is listed."""
    path = path or LIST_PATH
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        lines = (line.strip() for line in f)
        return {line.lower() for line in lines if line and not line.startswith("#")}


def is_listed(name, hashes) -> bool:
    return isinstance(name, str) and name_hash(name) in hashes


def drop_listed(df, name_col="Name", path=None, hashes=None):
    """`df` without listed athletes' rows, and how many rows were dropped."""
    hashes = load_hashes(path) if hashes is None else hashes
    if not hashes or df.empty:
        return df, 0
    # Hash each distinct name once (~70K names, not 330K rows).
    listed_names = {n for n in df[name_col].dropna().unique() if is_listed(n, hashes)}
    keep = ~df[name_col].isin(listed_names)
    return df[keep], int((~keep).sum())


def purge_csv(csv_path, hashes, name_col="Name") -> int:
    """Removes listed athletes' rows from a CSV, leaving every other line byte-for-byte as it was
    (rewriting it through pandas would reformat numbers and dates across the whole file).
    Returns the number of rows removed."""
    if not hashes or not os.path.exists(csv_path):
        return 0
    with open(csv_path, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    if not lines:
        return 0
    header = next(csv.reader([lines[0]]))
    col = header.index(name_col)

    kept, removed = [lines[0]], 0
    for line in lines[1:]:
        fields = next(csv.reader([line]), [])
        # One record per line is assumed (true of these files: no quoted newlines), so refuse
        # anything that doesn't parse to a full row rather than risk mangling the file.
        if line.strip() and len(fields) != len(header):
            raise ValueError(f"{csv_path}: unexpected line, not changing the file: {line[:120]!r}")
        if fields and is_listed(fields[col], hashes):
            removed += 1
        else:
            kept.append(line)

    if removed:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            f.writelines(kept)
    return removed


def count_rows(csv_path, name, name_col="Name") -> int:
    if not os.path.exists(csv_path):
        return 0
    key = name_key(name)
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for row in reader if name_key(row[name_col]) == key)


def purge_tracked_csvs(hashes) -> None:
    for path in TRACKED_CSVS:
        removed = purge_csv(path, hashes)
        print(f"  {os.path.relpath(path)}: removed {removed} rows")


def add(names, path=None) -> None:
    path = path or LIST_PATH
    hashes = load_hashes(path)
    new = []
    for name in names:
        h = name_hash(name)
        rows = count_rows(TRACKED_CSVS[0], name)
        status = "already listed" if h in hashes else "added"
        print(f"{name!r}: {status}; {rows} rows in {os.path.basename(TRACKED_CSVS[0])}")
        if rows == 0 and h not in hashes:
            print("  warning: no rows match this spelling - check the exact name on the site")
        if h not in hashes and h not in new:
            new.append(h)

    if new:
        exists = os.path.exists(path)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            if not exists:
                f.write(LIST_HEADER)
            f.writelines(h + "\n" for h in new)
        hashes |= set(new)

    print("Purging the tracked CSVs:")
    purge_tracked_csvs(hashes)
    print("Next: commit data/takedown_list.txt and the CSVs, then push to main to rebuild the site's table.")


def check(name, path=None) -> None:
    listed = name_hash(name) in load_hashes(path)
    print(f"{name!r}: {'listed' if listed else 'NOT listed'}")
    for csv_path in TRACKED_CSVS:
        print(f"  {os.path.relpath(csv_path)}: {count_rows(csv_path, name)} rows")


def main(argv) -> int:
    if len(argv) >= 2 and argv[0] == "add":
        add(argv[1:])
    elif len(argv) == 2 and argv[0] == "check":
        check(argv[1])
    elif argv == ["purge"]:
        hashes = load_hashes()
        print(f"{len(hashes)} names listed. Purging the tracked CSVs:")
        purge_tracked_csvs(hashes)
    else:
        print('usage: python transform/takedown.py add "NAME" ["NAME" ...] | check "NAME" | purge')
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
