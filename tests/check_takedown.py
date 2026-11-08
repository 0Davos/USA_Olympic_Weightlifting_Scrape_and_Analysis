"""Checks the takedown list (transform/takedown.py) and every place it is applied.

Uses temporary copies only: the real data/takedown_list.txt and the tracked CSVs are never changed.
  - name matching agrees with the website's own name key (app/api/index.py),
  - drop_listed removes every spelling variant the website would merge, and nothing else,
  - purging a CSV removes exactly the listed rows and leaves every other byte as it was,
  - `add` writes the list and purges, and a second `add` of the same name changes nothing,
  - meet_clean.py on the full raw CSV leaves no rows for a listed athlete and drops nothing else,
  - load_to_supabase.py's backup-table delete works against Supabase (a TEMPORARY table only;
    skipped without SUPABASE_DB_URL).

Run from the repo root:  python tests/check_takedown.py
"""

import csv
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "transform"))
sys.path.insert(0, str(ROOT / "app" / "api"))

import takedown as T  # noqa: E402

RAW_CSV = ROOT / "data" / "meet_results.csv"

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="takedown_check_"))
    try:
        run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    print(f"{len(failures)} FAILED: {failures}" if failures else "all checks passed")
    return 1 if failures else 0


def run(tmp):
    # ---- the name key is the website's
    from index import normalize  # app/api/index.py
    samples = ["Jane Doe", "  jane   DOE ", "Jane\tDoe", "JOSÉ  Núñez", "O'Brien-Smith", "Ann  Marie Lee"]
    check("name key matches the website's normalize() on tricky spellings",
          all(T.name_key(s) == normalize(s) for s in samples))

    # ---- drop_listed: spelling variants the site merges go; near-misses stay
    hashes = {T.name_hash("Jane Doe")}
    df = pd.DataFrame({"Name": ["Jane Doe", " jane  doe", "JANE DOE", "Jane Does", "John Doe", None],
                       "Total": [1, 2, 3, 4, 5, 6]})
    kept, n = T.drop_listed(df, hashes=hashes)
    check("drop_listed removes every variant the site would merge, and nothing else",
          n == 3 and kept["Total"].tolist() == [4, 5, 6], f"dropped {n}, kept totals {kept['Total'].tolist()}")
    kept, n = T.drop_listed(df, hashes=set())
    check("an empty list drops nothing", n == 0 and len(kept) == len(df))
    check("a missing list file means nobody is listed", T.load_hashes(str(tmp / "nope.txt")) == set())

    # ---- purge_csv on a real slice of the raw CSV (its own line endings), with the listed athlete inside
    with open(RAW_CSV, encoding="utf-8", newline="") as f:
        lines = [next(f) for _ in range(3001)]
    victim = next(iter(pd.read_csv(RAW_CSV, nrows=3000)["Name"].value_counts().index))  # most rows in the slice
    name_idx = next(csv.reader([lines[0]])).index("Name")
    expected = [l for l in lines[1:] if T.name_key(next(csv.reader([l]))[name_idx]) != T.name_key(victim)]
    csv_copy = tmp / "slice.csv"
    csv_copy.write_bytes("".join(lines).encode("utf-8"))
    removed = T.purge_csv(str(csv_copy), {T.name_hash(victim)})
    after = csv_copy.read_bytes().decode("utf-8")
    check("purge_csv removes exactly the listed athlete's rows",
          removed == 3000 - len(expected) and removed > 0, f"{removed} removed")
    check("purge_csv leaves every other line byte-for-byte (line endings included)",
          after == lines[0] + "".join(expected))
    check("purging again removes nothing", T.purge_csv(str(csv_copy), {T.name_hash(victim)}) == 0)

    bad = tmp / "bad.csv"
    bad.write_text("Meet,Date,Name\nA,2020-01-01,Jane Doe\nB,\"2020-01-02,Jane Doe\n", encoding="utf-8", newline="")
    before = bad.read_bytes()
    try:
        T.purge_csv(str(bad), hashes)
        refused = False
    except ValueError:
        refused = True
    check("a malformed CSV is refused and left unchanged", refused and bad.read_bytes() == before)

    # ---- add: writes the list, purges the tracked CSVs, and is idempotent
    list_copy = tmp / "takedown_list.txt"
    csv_copy.write_bytes("".join(lines).encode("utf-8"))
    original_csvs = T.TRACKED_CSVS
    T.TRACKED_CSVS = [str(csv_copy)]
    try:
        T.add([victim.upper() + "  "], path=str(list_copy))
        content_1 = list_copy.read_text(encoding="utf-8")
        T.add([victim], path=str(list_copy))
        content_2 = list_copy.read_text(encoding="utf-8")
    finally:
        T.TRACKED_CSVS = original_csvs
    check("add writes one hash line (and the header), not the name",
          T.load_hashes(str(list_copy)) == {T.name_hash(victim)} and victim.lower() not in content_1.lower()
          and content_1.startswith("# Athletes removed"))
    check("adding the same name again changes nothing", content_1 == content_2)
    check("add purged the CSV", T.count_rows(str(csv_copy), victim) == 0)

    # ---- meet_clean.py on the full raw CSV
    import meet_clean
    raw = pd.read_csv(RAW_CSV)
    counts = raw["Name"].map(T.name_key).value_counts()
    victim = counts.index[len(counts) // 3]  # an ordinary athlete with at least one row
    T_list = tmp / "one_name.txt"
    T_list.write_text(T.name_hash(victim) + "\n", encoding="utf-8")
    original_path = T.LIST_PATH
    try:
        T.LIST_PATH = str(tmp / "empty.txt")
        base = meet_clean.clean_meet_data(raw.copy())
        T.LIST_PATH = str(T_list)
        filtered = meet_clean.clean_meet_data(raw.copy())
    finally:
        T.LIST_PATH = original_path
    victim_rows = int((base["Name"].map(T.name_key) == victim).sum())
    check("meet_clean leaves no rows for a listed athlete",
          victim_rows > 0 and not (filtered["Name"].map(T.name_key) == victim).any(),
          f"{victim_rows} cleaned rows before")
    check("meet_clean drops nothing else",
          len(base) - len(filtered) == victim_rows
          and base[base["Name"].map(T.name_key) != victim].equals(filtered))

    # ---- load_to_supabase.py: deleting listed athletes from the backup table (temporary table only)
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    if not os.environ.get("SUPABASE_DB_URL"):
        print("SKIP backup-table delete (SUPABASE_DB_URL not set)")
        return
    from sqlalchemy import create_engine, text
    import load_to_supabase as L
    with create_engine(os.environ["SUPABASE_DB_URL"]).connect() as conn:
        conn.execute(text("CREATE TEMP TABLE t_backup (name text, total numeric)"))
        conn.execute(text("INSERT INTO t_backup VALUES ('Jane Doe', 1), (' jane  doe', 2), ('Jane Does', 3), "
                          "('John Doe', 4), (NULL, 5)"))
        n = L.delete_listed_rows(conn, hashes, "t_backup")
        left = [r[0] for r in conn.execute(text("SELECT total FROM t_backup ORDER BY total"))]
        check("delete_listed_rows removes the listed athlete's rows from a table, and nothing else",
              n == 2 and [int(v) for v in left] == [3, 4, 5], f"deleted {n}, left {left}")
        check("an empty list deletes nothing", L.delete_listed_rows(conn, set(), "t_backup") == 0)
        conn.rollback()


if __name__ == "__main__":
    sys.exit(main())
