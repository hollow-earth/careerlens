from collections import defaultdict
import tomllib
from re import search
from playwright.sync_api import sync_playwright
from time import sleep
from random import uniform
from urllib.parse import urlparse, urlunparse
from sqlite3 import Connection
from database import write_job_to_ingest, write_job_to_staging
from joblisting import JobListing
import scrapers.scraper_utilities as scraper_utilities

def linkedin_scrape_urls(conn: Connection):
    # Load config and throw everything into a search query
    config = scraper_utilities.load_config()

    # TODO: put that in scraper_utilities
    keywords = " OR ".join(f'"{item}"' for item in config["search"]["keywords"])
    location = config["search"]["locations"]
    time_filter = str(config["linkedin"]["time_filter"])
    distance = str(config["linkedin"]["distance"])

    # TODO: maybe rewrite this with urllib instead
    search_url = "https://www.linkedin.com/jobs/search?"
    if keywords:
        search_url += f"keywords={keywords}&"
    if location:
        search_url += f"location={location}&"
    if time_filter:
        search_url += f"f_TPR=r{time_filter}&"
    if distance:
        search_url += f"distance={distance}&"
    if search_url == "https://www.linkedin.com/jobs/search?":
        raise Exception("You need at least one search term for LinkedIn!")
    
    
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False) # TODO: switch to True when tests are over
        page = browser.new_page()
        page.goto(search_url)
        
        # Close the annoying pop ups
        dismiss_button = page.get_by_role("button", name="Dismiss")
        if dismiss_button.count() and dismiss_button.is_visible():
            dismiss_button.click()
        # TODO: this might make the program crash, add a check later
        page.get_by_role("button", name="Reject").click()
        # page.get_by_role("button", name="Close").click()
        
        # TODO: scroll to bottom to load all of the jobs
        job_cards = page.locator("ul.jobs-search__results-list > li")
        count = job_cards.count()
        i = 0
        
        while i < count:
            if dismiss_button.count() and dismiss_button.is_visible():
                dismiss_button.click()
            current_job = job_cards.nth(i)
            current_job.click()

            url = current_job.locator(".base-card__full-link").get_attribute("href")
            assert url is not None, "Expected href attribute to be a string, but got None"
            parsed_url = urlparse(url)              # Clean up the string before storing
            host = parsed_url.netloc
            domain_parts = host.split(".")
            if len(domain_parts) > 2:               # Strip the linkedin subdomain (ca, uk, etc.)
                host = ".".join(domain_parts[-2:])
            url = urlunparse((parsed_url.scheme, host, 
                parsed_url.path, '', '', ''))       # Strip useless tracking nonsense
            match = search(r"jobs/view/(?:.+\-)?(\d+)/?", url)
            assert match is not None, f"Regex failed to extract a Job ID from the URL: {url}"
            id = match.group(1).strip()

            write_job_to_ingest(conn, "LinkedIn", id, url)

            i += 1
            # Load more jobs if needed, then update the current list of jobs, then grab the next
            show_more_jobs_button = page.locator(".infinite-scroller__show-more-button")
            if show_more_jobs_button.count() and show_more_jobs_button.is_visible():
                if dismiss_button.count() and dismiss_button.is_visible():
                    dismiss_button.click()
                show_more_jobs_button.click()
                sleep(uniform(1.0, 3.0))
            job_cards = page.locator("ul.jobs-search__results-list > li")
            count = job_cards.count()
            sleep(uniform(1.0, 3.0))
        browser.close()

def linkedin_scraper(conn: Connection):
    linkedin_scrape_urls(conn)