from datetime import datetime, timezone
from random import uniform
from re import search
from sqlite3 import Connection
from time import sleep

from playwright.sync_api import Browser
from typing_extensions import Any

import database
from scrapers import scraper_utilities
from scrapers.scraper_utilities import (
    CompanyEntry,
    CompanyTrustStatus,
    JobEntry,
    JobFilters,
    JobSource,
    JobStatus,
)

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
        # TODO: assert has to be reaplced in the future with proper exceptions
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
        job = JobEntry(JobSource.LINKEDIN, job_id, scraped_url)
        if not database.job_exists_in_pipeline(conn, job):
            with conn:
                database.write_job_to_ingest(conn, job)
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
        job = database.get_next_ingest(conn, JobSource.LINKEDIN)
        if job is None:
            break

        _ = page.goto(job.url)
        dismiss_button = page.get_by_role("button", name="Dismiss")
        if dismiss_button.count() and dismiss_button.is_visible():
            dismiss_button.click()
        posting = page.locator(".details")

        job.title = posting.locator(".top-card-layout__title").inner_text().strip()
        job.company = posting.locator(".topcard__org-name-link").inner_text().strip()
        job.location = (
            posting.locator(".topcard__flavor-row")
            .locator(".topcard__flavor--bullet")
            .first.inner_text()
            .strip()
        )
        job.description = (
            posting.locator(".show-more-less-html__markup").inner_text().strip()
        )
        job.status = JobStatus.PENDING

        candidate_company = database.get_company(conn, scraper_utilities.normalize(job.company))
        if candidate_company is not None and candidate_company.trust_status.value == CompanyTrustStatus.BLOCKED.value:
            job.discard_reason = "Match in blacklisted_companies"
        elif filters.is_title_blacklisted(job.title):
            job.discard_reason = "Match in blacklisted_terms"

        if job.discard_reason:
            job.discarded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            job.status = JobStatus.DISCARDED
            with conn:
                database.write_job_to_discarded(conn, job)
                database.delete_from_ingest(conn, job)
            sleep(PAGE_DELAY)

        else:
            try:
                with conn:
                    database.write_job_to_staging(conn, job)
                    database.delete_from_ingest(conn, job)
                    database.write_company_to_companies(conn, CompanyEntry(job.company))
            except:
                raise Exception("Couldn't move row from ingest to staging!")
            sleep(PAGE_DELAY)

    page.close()


def linkedin_scraper(conn: Connection, browser: Browser, config: dict[str, Any], filters: JobFilters) -> None:
    linkedin_scrape_urls(conn, browser, config)
    linkedin_extract_url_contents(conn, browser, filters)
