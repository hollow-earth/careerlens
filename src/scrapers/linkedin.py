import tomllib
from re import search
from playwright.sync_api import sync_playwright
from time import sleep
from random import uniform
from urllib.parse import urlparse, urlunparse
from sqlite3 import Connection
from database import write_job_to_staging
from joblisting import JobListing

def linkedin_scraper(conn: Connection):
    # Load config and throw everything into a search query
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    
    keywords = " OR ".join(f'"{item}"' for item in config["search"]["keywords"])
    location = config["search"]["locations"]
    time_filter = str(config["search"]["time_filter"])
    distance = str(config["search"]["distance"])
    companies_to_skip = set(config["search"]["companies_to_skip"])
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
        browser = p.chromium.launch(headless=False) # TODO: switch to True when tests are over
        page = browser.new_page()
        page.goto(search_url)
        
        # Close the annoying pop ups
        page.get_by_role("button", name="Dismiss").click()
        page.get_by_role("button", name="Reject").click()
    
        # TODO: scroll to bottom to load all of the jobs
        job_cards = page.locator("ul.jobs-search__results-list > li")
        count = job_cards.count()
        i = 0
        while i < count:
            print(i)
            current_job = job_cards.nth(i)
            current_job.scroll_into_view_if_needed()
            current_job.click()
            page.get_by_role("button", name="Show more").click()
            
            _page_current_job = page.locator(".details-pane__content")
            title = _page_current_job.locator(".top-card-layout__title").inner_text().strip()
            description = _page_current_job.locator(".description__text").inner_text().strip()
            
            top_card = _page_current_job.locator(".topcard__flavor").all_inner_texts()
            company = top_card[0].strip()
            location = top_card[1].strip()
            
            link = _page_current_job.locator(".topcard__link").get_attribute("href")
            assert link is not None, "Expected href attribute to be a string, but got None"
            parsed_url = urlparse(link)             # Clean up the string before storing
            host = parsed_url.netloc
            domain_parts = host.split(".")
            if len(domain_parts) > 2:               # Strip the linkedin subdomain (ca, uk, etc.)
                host = ".".join(domain_parts[-2:])
            link = urlunparse((parsed_url.scheme, host, 
                parsed_url.path, '', '', ''))       # Strip useless tracking nonsense
            match = search(r"jobs/view/(?:.+\-)?(\d+)/?", link)
            assert match is not None, f"Regex failed to extract a Job ID from the URL: {link}"

            id = int(match.group(1).strip())
            
            # TODO: maybe add a location filter? Though LinkedIn is supposed to be the one handling that.
            if company not in companies_to_skip:
                job_listing = JobListing(id, title, company, description, location, "LinkedIn", link)
                write_job_to_staging(conn, job_listing)
            sleep(uniform(1.5, 3.0))
            i += 1
            count = job_cards.count()               # As we scroll down, we may load more jobs, so update the count as well
            if i == 2:
                break
        browser.close()
        
    # get_started = page.get_by_role("link", name="Get started")