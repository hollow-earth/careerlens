from random import uniform
from re import search
from sqlite3 import Connection
from time import sleep

from playwright.sync_api import Browser
from typing_extensions import Any

import database
from scrapers.scraper_utilities import JobEntry, JobStatus, JobFilters
from datetime import datetime, timezone

PAGE_DELAY = uniform(3.0, 5.0)
MAX_RETRIES = 3

def linkedin_scrape_urls(conn: Connection, browser: Browser, config: dict[str, Any]) -> None:
    # TODO: put that in scraper_utilities
    keywords = " OR ".join(f'"{item}"' for item in config["search"]["keywords"])
    location = config["search"]["location"]
    time_filter = config["linkedin"]["time_filter"]
    distance = config["linkedin"]["distance"]

    # TODO: maybe rewrite this with urllib instead
    search_url = "https://www.linkedin.com/jobs/search?"
    if keywords:
        search_url += f"keywords={keywords}&"
    if location:
        search_url += f"location={location}&"
    if time_filter:
        search_url += f"f_TPR=r{time_filter}&"
    if distance or distance == 0:
        search_url += f"distance={distance}&"
    if search_url == "https://www.linkedin.com/jobs/search?":
        raise Exception("You need at least one search term for LinkedIn!")

    page = browser.new_page()
    _ = page.goto(search_url)

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
        scraped_url = ""
        if dismiss_button.count() and dismiss_button.is_visible():
            dismiss_button.click()
        current_job = job_cards.nth(i)
        current_job.click()

        # Scrape URL first, remove the subdomain and text after jobs/view/{numerical_id}

        try:
            scraped_url = current_job.locator(".base-card__full-link").get_attribute("href")
        except:
            print(f"Scraping attempt failed")
            continue
        
        assert scraped_url is not None, (
            "Expected href attribute to be a string, but got None"
        )
        match = search(r"jobs/view/(?:.+\-)?(\d+)/?", scraped_url)
        assert match is not None, (
            f"Regex failed to extract a Job ID from the URL: {scraped_url}"
        )
        job_id = match.group(1).strip()
        scraped_url = f"https://www.linkedin.com/jobs/view/{job_id}"

        # If it already exists in ingest, staging, or jobs, skip adding to ingest
        if not database.job_exists_in_pipeline(conn, "linkedin", job_id, scraped_url):
            with conn:
                database.write_job_to_ingest(conn, "linkedin", job_id, scraped_url)
            print("Scraped job:", job_id, " ", scraped_url)

        # Load more jobs if needed, then update the current list of jobs, then grab the next
        show_more_jobs_button = page.locator(".infinite-scroller__show-more-button")
        if show_more_jobs_button.count() and show_more_jobs_button.is_visible() and count - i <= 5:
            if dismiss_button.count() and dismiss_button.is_visible() and count - i <= 5:
                dismiss_button.click()
                sleep(PAGE_DELAY)
            show_more_jobs_button.click()
            sleep(PAGE_DELAY)
        job_cards = page.locator("ul.jobs-search__results-list > li")
        count = job_cards.count()
        i += 1
        sleep(PAGE_DELAY)
    page.close()


def linkedin_extract_url_contents(conn: Connection, browser: Browser, filters:JobFilters) -> None:
    page = browser.new_page()
    while True:
        row = database.get_next_ingest(conn, "linkedin")
        if row is None:
            break
        row_id = row["id"]
        source = row["source"]
        job_id = row["job_id"]
        url = row["url"]

        _ = page.goto(url)
        dismiss_button = page.get_by_role("button", name="Dismiss")
        if dismiss_button.count() and dismiss_button.is_visible():
            dismiss_button.click()
        posting = page.locator(".details")
        title = posting.locator(".top-card-layout__title").inner_text().strip()
        company = posting.locator(".topcard__org-name-link").inner_text().strip()
        location = (
            posting.locator(".topcard__flavor-row")
            .locator(".topcard__flavor--bullet")
            .first.inner_text()
            .strip()
        )
        description = (
            posting.locator(".show-more-less-html__markup").inner_text().strip()
        )

        job = JobEntry(
            title = title,
            company = company,
            location = location,
            description = description,
            source = source,
            job_id = job_id,
            url = url,
            status = JobStatus.PENDING,
        )

        if filters.is_company_blacklisted(company):
            discard_reason = "Match in blacklisted_companies"
        elif filters.is_title_blacklisted(title):
            discard_reason = "Match in blacklisted_terms"
        else:
            discard_reason = None

        if discard_reason:
            with conn:
                database.write_job_to_discarded(conn, job, discard_reason,
                   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                database.delete_from_ingest(conn, row_id)
            sleep(PAGE_DELAY)
            continue
        
        try:
            with conn:
                database.write_job_to_staging(conn=conn, job=job)
                database.delete_from_ingest(conn=conn, ingest_id=row_id)
        except:
            raise Exception("Couldn't move row from ingest to staging!")
        sleep(PAGE_DELAY)

    page.close()


def linkedin_scraper(conn: Connection, browser: Browser, config: dict[str, Any], filters: JobFilters) -> None:
    linkedin_scrape_urls(conn, browser, config)
    linkedin_extract_url_contents(conn, browser, filters)
