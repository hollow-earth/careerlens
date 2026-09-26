from collections.abc import Callable
from datetime import datetime, timezone
from random import uniform
from sqlite3 import Connection
from time import sleep

from bs4 import BeautifulSoup
from playwright.sync_api import Page
from rich.text import Text
from typing_extensions import Any

import database
from scrapers.scraper_utilities import (
    CompanyEntry,
    CompanyTrustStatus,
    JobEntry,
    JobFilters,
    JobSource,
    JobStatus,
    select_directory,
)

PAGE_DELAY = uniform(5.0, 7.0)
MAX_RETRIES = 3
ProgressCallback = Callable[[Text | str], None]

def indeed_extract_contents(conn: Connection, filters:JobFilters, config: dict[str, Any], progress_callback: ProgressCallback) -> None:
    country_code = config["indeed"]["country_code"]
    dir = select_directory()
    if not dir:
        return
    for file in dir.iterdir():
        if file.suffix.lower() != ".html":
            continue
        try:
            html = file.read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            job_list = soup.select_one("ul.css-pygyny")

            if job_list is None:
                continue

            for job_card in job_list.find_all("li", recursive=False):
                card = job_card.select_one(".cardOutline")
                if not card or card.get("aria-hidden"):
                    continue

                card = job_card.select_one(".resultContent")
                if not card:
                    continue

                title_element = job_card.select_one("a.jcs-JobTitle")
                if title_element is None:
                    progress_callback(Text("Failed to extract job card contents!"))
                    continue 

                company_element = job_card.find("span", attrs={"data-testid": "company-name"})
                title = title_element.get_text(strip=True) if title_element else None
                company = company_element.get_text(strip=True) if company_element else None
                job_id = str(title_element.get("data-jk"))
                url = f"https://{country_code}.indeed.com/viewjob?jk={job_id}" if country_code else f"https://indeed.com/viewjob?jk={job_id}"
                if not job_id or not url:
                    progress_callback(Text(f"Scraping attempt failed for job_id {job_id}"))
                    continue

                job = JobEntry(title=title, company=company, job_id=job_id, url=url, source=JobSource.INDEED)
                if not database.job_exists_in_pipeline(conn, job):
                    with conn:
                        database.write_job_to_ingest(conn, job)
                    progress_callback(Text(f"Found job {job.title} at {job.company} with job_id {job.job_id}"))
                    if job.title is not None and job.company is not None:
                        with conn:
                            database.write_company_to_companies(conn, CompanyEntry(job.company))
                        candidate_company = database.get_company(conn, job.company)
                        if candidate_company is not None and candidate_company.trust_status.value == CompanyTrustStatus.BLOCKED.value:
                            job.discard_reason = "Match in blacklisted_companies"
                            progress_callback(Text("\t Job discarded due to match in blacklisted_companies"))
                        elif filters.is_title_blacklisted(job.title):
                            job.discard_reason = "Match in blacklisted_terms"
                            progress_callback(Text("\t Job discarded due to match in blacklisted_terms"))

                        if job.discard_reason:
                            job.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                            job.discarded_at = job.created_at
                            job.status = JobStatus.DISCARDED
                            with conn:
                                database.write_job_to_discarded(conn, job)
                                database.delete_from_ingest(conn, job)
                else:
                    progress_callback(Text(f"Job {job.title} at {job.company} with job_id {job.job_id} already in database!"))

        except Exception as error:
            progress_callback(Text(f"Failed to extract contents of file {file}: {error}"))
            continue

def indeed_extract_url_contents(conn: Connection, page: Page, filters:JobFilters, progress_callback: ProgressCallback) -> None:
    current_retries = 0
    while True:
        job = database.get_next_ingest(conn, JobSource.INDEED)
        if job is None:
            break
        try:
            _ = page.goto(job.url, wait_until="domcontentloaded")

            job.title = page.get_by_test_id("vj-job-title").inner_text().strip()
            metadata = page.get_by_test_id("company-info-metadata")
            company_link = metadata.locator("a")
            if company_link.count():
                job.company = company_link.first.inner_text().strip()
            else:
                job.company = metadata.get_by_test_id("vj-company-name").inner_text().strip()

            # This is quite fickle, keeping comments below for future tests
            job.location = metadata.locator(":scope > div").locator(":scope > div").nth(1).inner_text().strip() 
            #job.location = metadata.locator("div").last.inner_text().strip()
            #job.location = company_link.locator("xpath=../following-sibling::div[1]").inner_text()

            description = page.locator(".simple-job-description-html").inner_text().strip()
            compensation_text = metadata.locator("xpath=following-sibling::div[1]").inner_text().strip()
            job.description = compensation_text + "\n\n" + description
            job.status = JobStatus.READY
            progress_callback(Text(f"Found job {job.title} at {job.company} with job ID {job.job_id}"))
        except Exception as error:
            progress_callback(f"Error: {error}")
        try:
            with conn:
                database.write_job_to_staging(conn, job)
                database.delete_from_ingest(conn, job)
        except Exception as error:
            progress_callback(f"Couldn't move row from ingest to staging! Error: {error}")
            current_retries += 1
            if current_retries > MAX_RETRIES:
                break
            continue
        sleep(PAGE_DELAY)


def indeed_scraper(conn: Connection, config: dict[str, object], filters: JobFilters, page: Page, progress_callback: ProgressCallback) -> None:
    progress_callback(Text("Extracting Indeed job contents...", style="#f52bfb"))
    indeed_extract_contents(conn, filters, config, progress_callback)
    progress_callback(Text("Finished extracting Indeed job contents.", style="#f52bfb"))

    progress_callback(Text("Extracting LinkedIn job contents...", style="#f52bfb"))
    indeed_extract_url_contents(conn, page, filters, progress_callback)
    progress_callback(Text("Finished extracting LinkedIn job contents.", style="#f52bfb"))
