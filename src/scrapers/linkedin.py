from re import search
from playwright.sync_api import sync_playwright
from time import sleep
from random import uniform
from sqlite3 import Connection
from database import write_job_to_ingest
import scrapers.scraper_utilities as scraper_utilities

def linkedin_scrape_urls(conn: Connection) -> None:
    # Load config and throw everything into a search query
    config = scraper_utilities.load_config()

    # TODO: put that in scraper_utilities
    keywords = " OR ".join(f'"{item}"' for item in config["search"]["keywords"])
    location = config["search"]["location"]
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
            
            # Scrape URL first, remove the subdomain and text after jobs/view/{numerical_id}
            scraped_url = current_job.locator(".base-card__full-link").get_attribute("href")
            assert scraped_url is not None, "Expected href attribute to be a string, but got None"
            match = search(r"jobs/view/(?:.+\-)?(\d+)/?", scraped_url)
            assert match is not None, f"Regex failed to extract a Job ID from the URL: {scraped_url}"
            job_id = match.group(1).strip()
            scraped_url = f"https://www.linkedin.com/jobs/view/{job_id}"
            
            # If it already exists in ingest, staging, or jobs, skip adding to ingest
            if not scraper_utilities.job_exists_in_pipeline(conn, "linkedin", job_id):
                write_job_to_ingest(conn, "linkedin", job_id, scraped_url)
            
            # Load more jobs if needed, then update the current list of jobs, then grab the next
            show_more_jobs_button = page.locator(".infinite-scroller__show-more-button")
            if show_more_jobs_button.count() and show_more_jobs_button.is_visible():
                if dismiss_button.count() and dismiss_button.is_visible():
                    dismiss_button.click()
                show_more_jobs_button.click()
                sleep(uniform(1.0, 3.0))
            job_cards = page.locator("ul.jobs-search__results-list > li")
            count = job_cards.count()
            i += 1
            sleep(uniform(1.0, 3.0))
        browser.close()

def linkedin_extract_url_contents(conn: Connection) -> None:
    return

def linkedin_scraper(conn: Connection) -> None:
    linkedin_scrape_urls(conn)