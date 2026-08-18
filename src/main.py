import sqlite3

from playwright.sync_api import sync_playwright

import database
from scrapers.linkedin import linkedin_scraper


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
    # run_llm(get_prompt(prompt))

    try:
        database.close(conn)
    except sqlite3.Error as error:
        print(f"Error: {error}")
        return # TODO: change this to actually handle the error. Retry?

if __name__ == "__main__":
    main()