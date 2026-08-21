import sqlite3
import time
from datetime import datetime
from typing import Any

from playwright.sync_api import sync_playwright
from tomllib import load

import database
import llm
from scrapers.linkedin import linkedin_scraper
from scrapers.scraper_utilities import JobFilters


def load_config() -> tuple[dict[str, Any], JobFilters]:
    with open("config.toml", "rb") as f:
        config = load(f)
    return config, JobFilters(config)

def pipeline():
    config, filters = load_config()
    conn = database.connect()
    try:
        database.init_tables(conn)

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False) # TODO: switch to True when tests are over
            linkedin_scraper(conn, browser, config, filters)
            browser.close()
        # TODO: dedup time
        
        while True:
            start_time = time.perf_counter()
            row = database.get_next_staging(conn)
            if row is None:
                break
            
            id, job, created_at = row
            print(f"Processing job: {job.title}, at {job.company}")
            job_to_write = llm.use_llm(config, job)
            with conn:
                if job_to_write.score >= config["llm"]["minimum_score"]:
                    database.write_job_to_jobs(conn, job_to_write, created_at)
                else:
                    database.write_job_to_discarded(
                        conn, 
                        job_to_write, 
                        f"Score {job_to_write.score} below the minimum threshold of {config["llm"]["minimum_score"]}", 
                        created_at,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                database.delete_from_staging(conn, id)
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            print(f"Processing took {execution_time:.6f}s.\n")
            
    finally:
        try:
            database.close(conn)
        except sqlite3.Error as error:
            print(f"Error: {error}")