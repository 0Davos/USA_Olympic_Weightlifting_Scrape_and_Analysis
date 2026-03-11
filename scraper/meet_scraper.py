'''
Owen Davis
Meet Scraping Script
'''
import os
from datetime import datetime
from playwright.sync_api import sync_playwright 
import time
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

def scrape_meets():
    # Setup playwright
    with sync_playwright() as p:
        # --------------------------
        # Log into USAW
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://usaweightlifting.sport80.com/v/1023105/r/results?filters=eyJkYXRlX3JhbmdlX3N0YXJ0IjoiMjAyNS0wMS0wMSIsImRhdGVfcmFuZ2VfZW5kIjoiMjAyNS0xMi0zMSJ9")

        load_dotenv()
        SUPABASE_URL = os.environ["SUPABASE_URL"]
        SUPABASE_KEY = os.environ["SUPABASE_KEY"]
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("Error: Supabase credentials not found in environment variables")
            return
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
            security_code = input("Give us the security code :")

            page.fill("#deviceToken", security_code)
            page.press("#deviceToken", "Enter")

        print("PASSED - log into")
        # Log into USAW
        # --------------------------

        """
        # --------------------------
        # Click to right date

        # Click on that date range
        page.get_by_role("button", name="Show Filters").click()
        print("Clicked show filters (wifi button)")\
        
        page.click("#form__date_range_start")

        # loop to click into the desired past
        # Last month of meets is in January 2011
        year = str(datetime.now().year)
        target_month = f"January {year}"
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
        """

        # --------------------------
        # SCRAPING TIME
        all_data = []

        while True:
            meet_rows = page.locator("tr.row-clickable")
            meet_count = meet_rows.count()
            print(f"Found {meet_count} rows")

            # click through each meet on the current page
            for i in range(meet_count):
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

                    # Get current page number before clicking
                    #try:
                    #    current_page_text = meet_page.locator("button[aria-current='true']").inner_text(timeout=1000)
                    #    print(f"Current page: {current_page_text}")
                    #except:
                    #    print("Could not get current page number, but proceeding...")
                    
                    next_button.click()

                    # Wait for page to change - use a more robust wait
                    try:
                        # Wait for the table to update (rows might change)
                        meet_page.wait_for_timeout(1000)  # Brief pause
                        meet_page.wait_for_selector("table tbody tr:not([style*='display: none'])", timeout=10000)
                        print("Page updated successfully")
                    except Exception as e:
                        print(f"Page update wait failed: {e}")
                        # Try alternative wait
                        try:
                            meet_page.wait_for_function(
                                """() => {
                                    const rows = document.querySelectorAll('table tbody tr');
                                    return rows.length > 0;
                                }""",
                                timeout=10000
                            )
                        except:
                            print("Table did not update after Next — breaking.")
                            break
                    
                    page_num += 1
                        
                
                # go back to meet list
                meet_page.close()
                print(f"Completed scraping {meet_name}")
            
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

            try: 
                # Wait for the table to update (rows might change)
                page.wait_for_timeout(1000)  # Brief pause
                page.wait_for_selector("table tbody tr:not([style*='display: none'])", timeout=10000)
                print("Page updated successfully")
            except Exception as e:
                    print(f"Page update wait failed: {e}")
                    # Try alternative wait
                    try:
                        meet_page.wait_for_function(
                            """() => {
                                const rows = document.querySelectorAll('table tbody tr');
                                return rows.length > 0;
                            }""",
                            timeout=10000
                        )
                    except:
                        print("Table did not update after Next — breaking.")
                        break

        print(f"Scraping complete. Preparing to insert {len(all_data)} records to Supabase...")
        # SCRAPING TIME
        # --------------------------

        # --------------------------
        # Clean all_data
        supabase_data = []
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
                "WC_AgeGroup": row_cells[14] if len(row_cells) > 14 else "",
                "WC_Gender": row_cells[15] if len(row_cells) > 15 else "",
                "WC_BW": row_cells[16] if len(row_cells) > 16 else ""
            }
            supabase_data.append(athlete_dict)

        # Clean
        # --------------------------


        # --------------------------
        # Push to Supabase 
        if supabase_data:
            print(f"Found {len(supabase_data)} rows before deduplication")
            
            # Remove duplicates based on your unique constraint
            seen = set()
            deduped_data = []
            
            for row in supabase_data:
                # Create a unique key based on your constraint columns
                key = (row.get("Meet", ""), row.get("Name", ""), row.get("Bodyweight", ""))
                
                if key not in seen:
                    seen.add(key)
                    deduped_data.append(row)
            
            print(f"After deduplication: {len(deduped_data)} unique rows")
            
            try:
                response = supabase.table("meet_results").upsert(
                    deduped_data, 
                    on_conflict='Meet,Name,Bodyweight'
                ).execute()
                print(f"Successfully upserted {len(deduped_data)} records!")
            except Exception as e:
                print(f"Error inserting to Supabase: {e}")
        # Push to Supabase 
        # --------------------------


def overall_try():
    '''
    Function which catches any exceptions, returns False if there are any, True otherwise (passed with no fails)
    '''
    try:
        scrape_meets()
    except Exception as e:
        print(e)
        return False
    return True

if __name__ == '__main__':
    '''
    Loop to continously call until we succeed OR fail 10 times (don't want to exhaust)
    '''
    num_times_failed = 0
    while True:
        is_done = overall_try()
        if is_done == True:
            break
        num_times_failed += 1
        print(f"failed num: {num_times_failed}")
        print("----------------------------------------------")
        if num_times_failed > 5:
            print("FAILED - overall_try")
            break