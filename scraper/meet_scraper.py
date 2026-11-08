'''
Owen Davis
Meet Scraping Script
'''
import os
import sys
import argparse
import base64
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
import time
import pandas as pd
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "meet_results.csv")

sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "transform"))
from takedown import drop_listed  # noqa: E402  (athletes who asked to be removed: data/takedown_list.txt)


def parse_mixed_format_dates(date_series):
    """Parses a Date column/Series that may contain a mix of US (M/D/YYYY) and
    ISO (YYYY-MM-DD) formatted strings - the original bulk-loaded historical
    data uses US format, while this scraper's own output uses ISO. pandas'
    default date parsing infers a single format from the whole column and
    silently fails (NaT) on whichever format doesn't match, so both are tried
    explicitly here instead."""
    parsed = pd.to_datetime(date_series, format='%m/%d/%Y', errors='coerce')
    still_missing = parsed.isna()
    parsed.loc[still_missing] = pd.to_datetime(date_series[still_missing], format='%Y-%m-%d', errors='coerce')
    return parsed


def normalize_date_key(date_str):
    """Scalar version of parse_mixed_format_dates, for building dedup keys -
    normalizes a single Date value to YYYY-MM-DD so the same calendar date in
    different raw formats is recognized as the same date rather than as two
    different values. Falls back to the raw string if genuinely unparseable."""
    parsed = pd.to_datetime(date_str, format='%m/%d/%Y', errors='coerce')
    if pd.isna(parsed):
        parsed = pd.to_datetime(date_str, format='%Y-%m-%d', errors='coerce')
    if pd.isna(parsed):
        return str(date_str)
    return parsed.strftime('%Y-%m-%d')


SCRAPE_LOOKBACK_MONTHS = 3


def get_scrape_date_range():
    """Start = SCRAPE_LOOKBACK_MONTHS months before today, End = today.

    A fixed rolling window instead of "where the existing data stops". The old
    approach (start at the 1st of the month of the newest date already in the
    CSV) broke in two ways: future-dated rows from the source (e.g. a multi-
    week online meet dated past today) pushed the start date past meets that
    had not been scraped yet, and the cleaned CSV it read is only rebuilt on
    the user's machine, so an unattended weekly run could not rely on it to
    advance. Re-scraping the window each run costs time only: rows already in
    meet_results.csv are skipped by the (Meet, Date, Name, Bodyweight)
    dedup."""
    end_date = datetime.now()
    start_date = end_date - pd.DateOffset(months=SCRAPE_LOOKBACK_MONTHS)
    return start_date, end_date


def build_results_url(start_date, end_date):
    filters = {
        "date_range_start": start_date.strftime("%Y-%m-%d"),
        "date_range_end": end_date.strftime("%Y-%m-%d"),
    }
    encoded = base64.b64encode(json.dumps(filters, separators=(',', ':')).encode()).decode()
    return f"https://usaweightlifting.sport80.com/v/1023105/r/results?filters={encoded}"


CODE_WAIT_SECONDS = 300
CODE_POLL_SECONDS = 2


def get_security_code(code_file=None, timeout_seconds=CODE_WAIT_SECONDS, poll_seconds=CODE_POLL_SECONDS):
    """Returns the 2FA code. With no code_file, asks on the terminal with
    input() (the normal, manual run). With a code_file, an unattended run
    polls that file until it holds a code (the last non-empty line wins),
    clears the file so the code can't be reused, and returns it; raises
    TimeoutError if none arrives within timeout_seconds. The file is read as
    utf-8-sig so a byte-order mark added by Windows PowerShell is ignored. The
    caller should empty the file before the run, or a stale code left from the
    previous run would be used first."""
    if not code_file:
        return input("Give us the security code :")

    print(f"Waiting up to {timeout_seconds}s for the code in {code_file}...")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if os.path.exists(code_file):
            with open(code_file, encoding="utf-8-sig") as f:
                lines = [line.strip() for line in f.read().splitlines() if line.strip()]
            if lines:
                open(code_file, "w").close()
                return lines[-1]
        time.sleep(poll_seconds)
    raise TimeoutError(f"No security code appeared in {code_file} within {timeout_seconds}s")


def scrape_meets(code_file=None):
    # --- ONE-TIME RECOVERY OVERRIDE ---
    # Manually scrapes from 2025-01-01 (the earliest date any incrementally-
    # scraped row could exist - the very first scraper run used a hardcoded
    # 2025-01-01 start) through today, instead of the normal auto-computed
    # range. Recovers rows wrongly dropped by two now-fixed bugs: the old
    # (Meet, Name, Bodyweight) dedup key without Date, and
    # get_scrape_date_range() being blind to this scraper's own previously-
    # appended ISO-format dates. Set RECOVERY_MODE to False (or delete this
    # block) once this recovery run is done, to resume normal operation via
    # get_scrape_date_range().
    RECOVERY_MODE = False

    if RECOVERY_MODE:
        start_date = datetime(2025, 1, 1)
        end_date = datetime.now()
    else:
        start_date, end_date = get_scrape_date_range()

    url = build_results_url(start_date, end_date)
    print(f"Scraping date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Setup playwright
    with sync_playwright() as p:
        # --------------------------
        # Log into USAW
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        load_dotenv()

        email = os.environ["USAW_EMAIL"]
        password = os.environ["USAW_PASSWORD"]
        if not email or not password:
            print("Error: email/password credentials not found in environment variables")
            return
        
        # Fill out username and password
        page.fill("#username", email)
        page.press("#username", "Tab") 
        page.fill("#password", password)

        # press enter
        page.press("#password", "Enter")

        try:
            page.wait_for_selector("#deviceToken", timeout=10000)
        except:
            pass
        if page.locator("#deviceToken").count() > 0:
            print("Device confirmation required — waiting for code...")
            security_code = get_security_code(code_file)

            page.fill("#deviceToken", security_code)
            page.press("#deviceToken", "Enter")

        print("PASSED - log into")
        # Log into USAW
        # --------------------------


        '''
        # --------------------------
        # Click to right date

        # Click on that date range
        page.get_by_role("button", name="Show Filters").click()
        print("Clicked show filters (wifi button)")\

        page.click("#form__date_range_start")

        # loop to click into the desired past
        # Last month of meets is in January 2011
        year = str(datetime.now().year)
        target_month = "August 2025"#f"January {year}"
        month_button = page.locator("div.v-date-picker-header__value button").first
        while True:
            current_month = month_button.inner_text()
            print(current_month)
            if current_month == target_month:
                print(f"Reached {target_month}")
                break

            page.get_by_role("button", name="Previous month").click()

        # click first of the month, then apply button
        page.locator("button.v-btn", has_text="1").first.click()
        page.locator("button:has-text('Apply')").click()

        print("PASSED - click to right month")
        # Click to right month
        # --------------------------
        '''


        # --------------------------
        # SCRAPING TIME
        all_data = []

        while True:
            meet_rows = page.locator("tr.row-clickable")
            meet_count = meet_rows.count()
            print(f"Found {meet_count} rows")

            # Signature of this page's content, captured before we move on - used
            # below to verify the next page of meets actually loaded.
            first_meet_signature = meet_rows.first.inner_text() if meet_count > 0 else ""

            # click through each meet on the current page
            for i in range(meet_count):
                meet_name = None
                meet_page = None
                try:
                    # select meet and name
                    meet_rows = page.locator("tr.row-clickable")
                    meet_row = meet_rows.nth(i)
                    meet_name = meet_row.inner_text().split("\n")[0]
                    print(f"Clicking meet: {meet_name}")

                    # Click meet row and wait for new page
                    with page.context.expect_page() as new_page_info:
                        meet_row.click()
                    meet_page = new_page_info.value
                    meet_page.wait_for_load_state("networkidle")
                    # wait for the results table to appear
                    meet_page.wait_for_selector("table thead:has-text('Lifter')")

                    # scrape all athlete rows
                    page_num = 1
                    max_pages = 100

                    while page_num <= max_pages:
                        print(f"Processing page {page_num}")

                        # Wait for table to load
                        meet_page.wait_for_selector("table tbody tr", timeout=10000)

                        # each page
                        athlete_rows = meet_page.locator("table tbody tr")
                        athlete_count = athlete_rows.count()
                        print(f"Found {athlete_count} athletes on page {page_num}")

                        # Signature of this page's content, captured before we move on -
                        # used below to verify the next page actually loaded, rather than
                        # just waiting a fixed amount of time and hoping.
                        first_row_signature = athlete_rows.first.inner_text() if athlete_count > 0 else ""

                        for j in range(athlete_count):
                            try:
                                row_cells = meet_page.evaluate("""(index) => {
                                    const row = document.querySelectorAll('table tbody tr')[index];
                                    if (!row) return [];
                                    return Array.from(row.querySelectorAll('td div')).map(d => d.textContent.trim());
                                }""", j)
                                all_data.append(row_cells)
                            except Exception as e:
                                print(f"Error getting row {j}: {e}")

                        next_button = meet_page.locator("button[aria-label='Next page']:not([disabled])")

                        if next_button.count() == 0:
                            print("No more pages for this meet.")
                            break

                        next_button.click()

                        # Wait for the table's content to actually change to the new page,
                        # not just for "some rows" to exist - which could still be the
                        # previous page's rows lingering during the transition.
                        try:
                            meet_page.wait_for_function(
                                """(oldFirstRowText) => {
                                    const row = document.querySelector('table tbody tr');
                                    return row && row.innerText.trim() !== oldFirstRowText;
                                }""",
                                arg=first_row_signature,
                                timeout=10000
                            )
                            print("Page updated successfully")
                        except Exception as e:
                            print(f"Page content did not change after Next — breaking: {e}")
                            break

                        page_num += 1

                    # go back to meet list
                    meet_page.close()
                    print(f"Completed scraping {meet_name}")
                except Exception as e:
                    print(f"Skipping meet at index {i} ({meet_name or 'name unknown'}) due to error: {e}")
                    if meet_page is not None:
                        try:
                            meet_page.close()
                        except Exception:
                            pass
            
            # now, move to next page of meets
            next_page_of_meets = page.locator("button[aria-label='Next page']:not([disabled])")
            if next_page_of_meets.count() == 0:
                print("No more pages of meets")
                break
            try:
                current_page_text = page.locator("button[aria-current='true']").inner_text(timeout=5000)
                print(f"Current page: {current_page_text}")
            except:
                print("Could not get current page number, but proceeding...")
            next_page_of_meets.click()

            # Wait for the meets table's content to actually change to the new page,
            # not just for "some rows" to exist - which could still be the previous
            # page's rows lingering during the transition.
            try:
                page.wait_for_function(
                    """(oldFirstRowText) => {
                        const row = document.querySelector('tr.row-clickable');
                        return row && row.innerText.trim() !== oldFirstRowText;
                    }""",
                    arg=first_meet_signature,
                    timeout=10000
                )
                print("Page updated successfully")
            except Exception as e:
                print(f"Page content did not change after Next — breaking: {e}")
                break

        print(f"Scraping complete. Preparing to process {len(all_data)} records...")
        # SCRAPING TIME
        # --------------------------

        # --------------------------
        # Clean all_data
        parsed_data = []
        for row_cells in all_data:
            # Map each row to dictionary with your column names
            athlete_dict = {
                "Meet": row_cells[0] if len(row_cells) > 0 else "",
                "Date": row_cells[1] if len(row_cells) > 1 else "",
                "Weight Category": row_cells[2] if len(row_cells) > 2 else "",
                "Name": row_cells[3] if len(row_cells) > 3 else "",
                "Bodyweight": row_cells[4] if len(row_cells) > 4 else None,
                "Sn#1": row_cells[5] if len(row_cells) > 5 else None,
                "Sn#2": row_cells[6] if len(row_cells) > 6 else None,
                "Sn#3": row_cells[7] if len(row_cells) > 7 else None,
                "CJ#1": row_cells[8] if len(row_cells) > 8 else None,
                "CJ#2": row_cells[9] if len(row_cells) > 9 else None,
                "CJ#3": row_cells[10] if len(row_cells) > 10 else None,
                "Best Sn": row_cells[11] if len(row_cells) > 11 else None,
                "Best CJ": row_cells[12] if len(row_cells) > 12 else None,
                "Total": row_cells[13] if len(row_cells) > 13 else None,
            }
            parsed_data.append(athlete_dict)

        # Clean
        # --------------------------


        # --------------------------
        # Append to CSV
        if parsed_data:
            print(f"Found {len(parsed_data)} rows before deduplication")

            # Remove duplicates based on the unique constraint
            seen = set()
            deduped_data = []

            for row in parsed_data:
                # Create a unique key based on the constraint columns. Includes Date
                # because many meets (e.g. "Bay State Games", "The Minnesota Open")
                # recur annually under the exact same Meet name with no year in it -
                # without Date, a returning athlete competing at a similar bodyweight
                # in a later year's edition would be wrongly treated as a duplicate
                # of their earlier entry and silently dropped. Date is normalized
                # (not compared as a raw string) since the CSV has a mix of US and
                # ISO date formats - see parse_mixed_format_dates/normalize_date_key.
                key = (
                    row.get("Meet", ""),
                    normalize_date_key(row.get("Date", "")),
                    row.get("Name", ""),
                    row.get("Bodyweight", ""),
                )

                if key not in seen:
                    seen.add(key)
                    deduped_data.append(row)

            print(f"After deduplication: {len(deduped_data)} unique rows")

            new_df = pd.DataFrame(deduped_data)
            # Never store new rows for athletes who asked to be removed.
            new_df, n_listed = drop_listed(new_df)
            if n_listed:
                print(f"Takedown list: skipped {n_listed} rows")
            file_exists = os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0

            if file_exists:
                # Drop any rows already present in the CSV, keyed the same way as above.
                # Dates are normalized (vectorized, since existing_df can be 300K+ rows)
                # rather than compared as raw strings, for the same reason as above.
                existing_df = pd.read_csv(CSV_PATH, dtype=str)
                existing_dates_parsed = parse_mixed_format_dates(existing_df["Date"])
                existing_dates_normalized = existing_dates_parsed.dt.strftime('%Y-%m-%d')
                existing_dates_normalized = existing_dates_normalized.fillna(existing_df["Date"].astype(str))

                existing_keys = set(zip(
                    existing_df["Meet"].astype(str),
                    existing_dates_normalized,
                    existing_df["Name"].astype(str),
                    existing_df["Bodyweight"].astype(str),
                ))

                new_dates_parsed = parse_mixed_format_dates(new_df["Date"])
                new_dates_normalized = new_dates_parsed.dt.strftime('%Y-%m-%d')
                new_dates_normalized = new_dates_normalized.fillna(new_df["Date"].astype(str))

                new_keys = list(zip(
                    new_df["Meet"].astype(str),
                    new_dates_normalized,
                    new_df["Name"].astype(str),
                    new_df["Bodyweight"].astype(str),
                ))
                keep_mask = [key not in existing_keys for key in new_keys]
                new_df = new_df[keep_mask]

            if new_df.empty:
                print("No new rows to append — CSV already up to date.")
            else:
                new_df.to_csv(CSV_PATH, mode='a', header=not file_exists, index=False)
                print(f"Appended {len(new_df)} new rows to {CSV_PATH}")
        # Append to CSV
        # --------------------------


def overall_try(code_file=None):
    '''
    Function which catches any exceptions, returns False if there are any, True otherwise (passed with no fails)
    '''
    try:
        scrape_meets(code_file)
    except Exception as e:
        print(e)
        return False
    return True

if __name__ == '__main__':
    '''
    Loop to continously call until we succeed OR fail 10 times (don't want to exhaust)
    '''
    parser = argparse.ArgumentParser(description="Scrape USAW meet results into data/meet_results.csv")
    parser.add_argument(
        "--code-file",
        help="For unattended runs: read the 2FA code from this file instead of asking on the terminal "
             "(empty the file before the run; it is cleared again once the code is read)",
    )
    args = parser.parse_args()

    num_times_failed = 0
    while True:
        is_done = overall_try(args.code_file)
        if is_done == True:
            break
        num_times_failed += 1
        print(f"failed num: {num_times_failed}")
        print("----------------------------------------------")
        if num_times_failed > 5:
            print("FAILED - overall_try")
            break