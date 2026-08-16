import database
import sqlite3
from scrapers.linkedin import linkedin_scraper
from playwright.sync_api import sync_playwright

def main():
    try:
        conn = database.connect()
    except sqlite3.Error as error:
        print(f"Error: {error}")
        raise
    
    conn.row_factory = sqlite3.Row
    database.init_tables(conn)
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False) # TODO: switch to True when tests are over
        linkedin_scraper(conn, browser)
        browser.close()
    
    try:
        database.close(conn)
    except sqlite3.Error as error:
        print(f"Error: {error}")
        raise # TODO: change this to actually handle the error. Retry?

if __name__ == "__main__":
    main()