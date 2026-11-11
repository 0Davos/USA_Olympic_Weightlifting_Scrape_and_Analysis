'''
One-off backfill: fills the "Meet Level" and "Meet Results" columns of data/meet_results.csv for rows
scraped before meet_scraper.py started recording them.

Two steps:
  1. Fetch - reads USAW's public meet list (no login needed) with Playwright, month by month and in
     windows small enough to fit on one page (see fetch_window for why), and saves every meet's name,
     level, date and number of results to data/meet_list.csv. Skipped if that file already exists,
     unless --refetch is given.
  2. Apply - matches each CSV row to a meet on that list and writes the two columns into
     data/meet_results.csv (every other column is left exactly as it was). --dry-run reports the matching
     without writing.

Matching: the list has no ID that the CSV shares, so a row is matched by meet name (whitespace and case
ignored) plus date. The list's date is usually the meet's LAST day, and a row's date is its session's
day, so a row goes to the same-name meet whose list date is the soonest on or after the row's date
(within MAX_DAYS_AFTER; many meet names recur every year). Failing that, the nearest list date up to
MAX_DAYS_BEFORE before the row's date is accepted: the 2020-21 online meets are listed by their FIRST
day, with results dated weeks later. Two same-name meets tied for a row leave it blank, as do names not on
the list. The report then checks each matched meet's row count against its listed number of results.

    python scraper/backfill_meet_info.py [--refetch] [--dry-run]
'''
import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from playwright.sync_api import sync_playwright

from meet_scraper import (
    CSV_PATH, MEET_LEVEL_COL, MEET_RESULTS_COL,
    encode_date_filter, parse_meet_list_row, parse_mixed_format_dates, read_meet_list_headers,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEET_LIST_PATH = os.path.join(SCRIPT_DIR, "..", "data", "meet_list.csv")
PUBLIC_LIST_URL = "https://usaweightlifting.sport80.com/public/rankings/results"

MAX_DAYS_AFTER = 60   # longest gap allowed from a row's date to its meet's last day (multi-week online meets)
MAX_DAYS_BEFORE = 90  # fallback: a list date before the row's date (online meets of 2020-21 are listed
                      # by their first day, with results dated weeks later)
PAGE_PAUSE_SECONDS = 0.5  # between page loads, to go easy on the site
EARLIEST_LIST_YEAR = 2011
PAGE_SIZE = 30            # meets per page on the list (its default)


# ---------------------------------------------------------------- fetch

def _rows_on_page(page, headers):
    cells_per_row = page.evaluate("""() => Array.from(document.querySelectorAll('tr.row-clickable'))
        .map(r => Array.from(r.querySelectorAll('td')).map(td => td.innerText.trim()))""")
    return [parse_meet_list_row(cells, headers) for cells in cells_per_row]


def _record_count(page):
    """The "N Records" figure shown above the list, or None if it can't be read."""
    try:
        text = page.get_by_text(re.compile(r"^\s*[\d,]+ Records?\s*$")).first.inner_text(timeout=5000)
        return int(text.split()[0].replace(",", ""))
    except Exception:
        return None


def _load_window(page, start, end):
    """Opens the list for start..end (inclusive dates) and returns its "N Records" figure. The list's
    filter leaves out meets ON its start date (checked 2026-11-11: 2013-11-02..2013-11-03 lists only the
    11-03 meets), so the filter starts the day before."""
    page.goto(f"{PUBLIC_LIST_URL}?filters={encode_date_filter(start - timedelta(days=1), end)}")
    page.wait_for_load_state("networkidle")
    time.sleep(PAGE_PAUSE_SECONDS)
    expected = _record_count(page)
    if expected is None:
        raise RuntimeError(f"Couldn't read the record count for {start:%Y-%m-%d}..{end:%Y-%m-%d}")
    if expected:
        page.wait_for_selector("tr.row-clickable", timeout=15000)
    return expected


def _collect_pages(page, headers):
    """Pages through the current list. Only used when a single day has more than a page of meets."""
    meets = []
    while True:
        meets.extend(_rows_on_page(page, headers))
        next_button = page.locator("button[aria-label='Next page']:not([disabled])")
        if next_button.count() == 0:
            return meets
        first_row = page.locator("tr.row-clickable").first.inner_text()
        next_button.first.click()
        page.wait_for_function(
            """(old) => { const r = document.querySelector('tr.row-clickable');
                          return r && r.innerText.trim() !== old; }""",
            arg=first_row, timeout=15000,
        )
        time.sleep(PAGE_PAUSE_SECONDS)


def fetch_window(page, start, end, problems):
    """Every meet listed with a date in start..end. The list is ordered by date only, so meets sharing a
    date can swap places between page loads: paging through a long list returned some meets twice and
    skipped others (337 of ~7,500 in a first, year-by-year run). So a window is only read when it fits
    on one page; a bigger one is split in half and each half fetched on its own. A single day with more
    than a page of meets has to be paged; it's de-duplicated and noted in `problems` if meets may be
    missing."""
    expected = _load_window(page, start, end)
    if expected == 0:
        return []
    headers = read_meet_list_headers(page)
    if "Level" not in headers or "Results" not in headers:
        raise RuntimeError(f"Meet list has no Level/Results column (headers: {headers})")

    if expected > PAGE_SIZE and start < end:
        mid = start + (end - start) / 2
        mid = datetime(mid.year, mid.month, mid.day)
        return (fetch_window(page, start, mid, problems)
                + fetch_window(page, mid + timedelta(days=1), end, problems))

    meets = _rows_on_page(page, headers) if expected <= PAGE_SIZE else _collect_pages(page, headers)
    unique = list({tuple(m.values()): m for m in meets}.values())
    if len(unique) != expected:
        problems.append(f"{start:%Y-%m-%d}..{end:%Y-%m-%d}: read {len(unique)} meets, the list says {expected}")
    return unique


def fetch_meet_list(first_year, last_year):
    meets, problems = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for year in range(first_year, last_year + 1):
            year_meets = []
            for month in range(1, 13):
                start = datetime(year, month, 1)
                end = (datetime(year + month // 12, month % 12 + 1, 1) - timedelta(days=1))
                year_meets.extend(fetch_window(page, start, end, problems))
            print(f"{year}: {len(year_meets)} meets")
            meets.extend(year_meets)
        # Cross-check: the windows together must hold every meet the list has for the whole range.
        total = _load_window(page, datetime(first_year, 1, 1), datetime(last_year, 12, 31))
        print(f"Total: {len(meets)} meets read, the list says {total} for {first_year}-{last_year}")
        if total != len(meets):
            problems.append(f"whole range: read {len(meets)} meets, the list says {total}")
        browser.close()
    for problem in problems:
        print(f"Warning: {problem}")
    df = pd.DataFrame(meets, columns=["Meet", "Level", "Date", "Results"])
    df["Results"] = df["Results"].astype("Int64")
    df.to_csv(MEET_LIST_PATH, index=False)
    print(f"Saved {len(df)} meets to {MEET_LIST_PATH}")
    return df


# ---------------------------------------------------------------- apply

def _name_key(name):
    return re.sub(r"\s+", " ", str(name)).strip().casefold()


def match_rows(raw, meet_list):
    """For each row of `raw`, the index into `meet_list` of its meet (or -1), plus why unmatched rows
    weren't matched. Works on unique (name, date) pairs, then maps back to rows."""
    list_dates = pd.to_datetime(meet_list["Date"], format="%Y-%m-%d", errors="coerce")
    by_name = {}
    for idx, (name, date) in enumerate(zip(meet_list["Meet"], list_dates)):
        by_name.setdefault(_name_key(name), []).append((date, idx))

    keys = raw["Meet"].map(_name_key)
    dates = parse_mixed_format_dates(raw["Date"])
    pairs = pd.DataFrame({"key": keys, "date": dates}).drop_duplicates()

    def pick(key, date):
        candidates = by_name.get(key)
        if not candidates:
            return -1, "meet name not on the list"
        if pd.isna(date):
            return (candidates[0][1], "") if len(candidates) == 1 else (-1, "undated row, name not unique")
        deltas = [((ld - date).days, idx) for ld, idx in candidates if not pd.isna(ld)]
        for lo, hi, use_abs in [(0, MAX_DAYS_AFTER, False), (-MAX_DAYS_BEFORE, -1, True)]:
            within = [(abs(d) if use_abs else d, idx) for d, idx in deltas if lo <= d <= hi]
            if within:
                best = min(d for d, _ in within)
                tied = [idx for d, idx in within if d == best]
                if len(tied) > 1:
                    return -1, "two same-name meets on the same date"
                return tied[0], ""
        return -1, "no same-name meet near this date"

    picked = {(k, d): pick(k, d) for k, d in zip(pairs["key"], pairs["date"])}
    lookup = [picked[(k, d)] for k, d in zip(keys, dates)]
    return [m for m, _ in lookup], [why for _, why in lookup]


def report(raw, meet_list, matched, reasons):
    matched = pd.Series(matched, index=raw.index)
    n = len(raw)
    ok = matched >= 0
    print(f"\nRows matched: {ok.sum():,} of {n:,} ({ok.mean():.1%})")
    why = pd.Series(reasons, index=raw.index)[~ok]
    for reason, count in why.value_counts().items():
        print(f"  unmatched - {reason}: {count:,} rows")
    if (~ok).any():
        sample = raw.loc[~ok, ["Meet", "Date"]].drop_duplicates().head(10)
        print("  e.g.\n" + sample.to_string(index=False))

    # Each matched meet's row count vs its listed number of results. Counted on unique results, since
    # the raw CSV holds some exact duplicate rows (meet_clean.py drops them).
    unique = raw.assign(_m=matched).drop_duplicates(subset=["Meet", "Date", "Name", "Bodyweight", "Total"])
    counts = unique.loc[unique["_m"] >= 0].groupby("_m").size()
    listed = meet_list["Results"].iloc[counts.index].to_numpy()
    diff = counts.to_numpy() - listed
    print(f"\nMeets matched: {len(counts):,} of {len(meet_list):,} on the list")
    print(f"  row count equals listed results: {(diff == 0).sum():,}")
    print(f"  more rows than listed: {(diff > 0).sum():,}   fewer rows than listed: {(diff < 0).sum():,}")
    off = pd.DataFrame({"meet": meet_list["Meet"].iloc[counts.index].to_numpy(),
                        "date": meet_list["Date"].iloc[counts.index].to_numpy(),
                        "rows": counts.to_numpy(), "listed": listed, "diff": diff})
    off = off[off["diff"] != 0]
    off = off.loc[off["diff"].abs().sort_values(ascending=False).index]
    if len(off):
        print("  largest differences:\n" + off.head(10).to_string(index=False))

    levels = meet_list["Level"].iloc[matched[ok]].value_counts()
    print("\nMatched rows by meet level:\n" + levels.to_string())


def apply_meet_list(meet_list, dry_run=False):
    # Everything read as text, nothing turned into NaN, so the other columns are written back unchanged.
    raw = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)
    original_cols = [c for c in raw.columns if c not in (MEET_LEVEL_COL, MEET_RESULTS_COL)]

    matched, reasons = match_rows(raw, meet_list)
    report(raw, meet_list, matched, reasons)
    if dry_run:
        print("\nDry run - nothing written")
        return

    levels = meet_list["Level"].fillna("").astype(str).tolist()
    results = ["" if pd.isna(r) else str(int(r)) for r in meet_list["Results"]]
    raw[MEET_LEVEL_COL] = [levels[m] if m >= 0 else "" for m in matched]
    raw[MEET_RESULTS_COL] = [results[m] if m >= 0 else "" for m in matched]

    # Write to a temporary file, check every original column survived unchanged, then replace.
    tmp_path = CSV_PATH + ".tmp"
    raw.to_csv(tmp_path, index=False)
    check = pd.read_csv(tmp_path, dtype=str, keep_default_na=False)
    before = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)[original_cols]
    if not check[original_cols].equals(before):
        os.remove(tmp_path)
        raise RuntimeError("Rewritten CSV doesn't match the original columns - nothing written")
    os.replace(tmp_path, CSV_PATH)
    print(f"\nWrote {MEET_LEVEL_COL!r} and {MEET_RESULTS_COL!r} to {len(raw):,} rows of {CSV_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill meet level and size into data/meet_results.csv")
    parser.add_argument("--refetch", action="store_true", help="re-read the meet list even if data/meet_list.csv exists")
    parser.add_argument("--dry-run", action="store_true", help="report the matching without writing the CSV")
    args = parser.parse_args()

    if args.refetch or not os.path.exists(MEET_LIST_PATH):
        dates = parse_mixed_format_dates(pd.read_csv(CSV_PATH, dtype=str, usecols=["Date"])["Date"])
        # The raw CSV has a few dozen junk dates going back to 1905 (looks like birthdates typed into
        # the date field); USAW's online records start in 2011, so earlier years are skipped.
        first_year = max(int(dates.min().year), EARLIEST_LIST_YEAR)
        last_year = max(datetime.now().year, int(dates.max().year))
        print(f"Fetching the meet list for {first_year}-{last_year}...")
        meet_list = fetch_meet_list(first_year, last_year)
    else:
        print(f"Using the saved meet list in {MEET_LIST_PATH} (--refetch to re-read it)")
        meet_list = pd.read_csv(MEET_LIST_PATH, dtype=str, keep_default_na=False)
        meet_list["Results"] = pd.to_numeric(meet_list["Results"], errors="coerce").astype("Int64")

    apply_meet_list(meet_list, dry_run=args.dry_run)
    sys.exit(0)
