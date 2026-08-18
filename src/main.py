import sqlite3

from playwright.sync_api import sync_playwright

import database
import llm
from scrapers import scraper_utilities
from scrapers.linkedin import linkedin_scraper


# TODO: replace scraper_utilities at some point, move config somewhere more natural

def main():
    try:
        conn = database.connect()
    except sqlite3.Error as error:
        print(f"Error: {error}")
        return
    
    database.init_tables(conn)
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True) # TODO: switch to True when tests are over
        linkedin_scraper(conn, browser)
        browser.close()
    # TODO: dedup time
    
    while True:
        row = database.get_next_staging(conn)
        if row is None:
            break
    # run_llm(get_prompt(prompt))

    try:
        database.close(conn)
    except sqlite3.Error as error:
        print(f"Error: {error}")
        return # TODO: change this to actually handle the error. Retry?

if __name__ == "__main__":
    main()
