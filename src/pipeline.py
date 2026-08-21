import sqlite3
import time
from datetime import datetime
from typing import Any

from playwright.sync_api import sync_playwright
from tomllib import load

import database
import llm
from scrapers.linkedin import linkedin_scraper
from scrapers.scraper_utilities import JobData, JobFilters


def load_config() -> tuple[dict[str, Any], JobFilters]:
    with open("config.toml", "rb") as f:
        config = load(f)
    return config, JobFilters(config)

def process_job_with_llm(conn: sqlite3.Connection, config: dict[str, Any], row: tuple[int, JobData, str]) -> None:
    id, job, created_at = row
    min_score = config["llm"]["minimum_score"]
    print(f"Processing job: {job.title}, at {job.company}")
    job_to_write = llm.use_llm(config, job)
    with conn:
        if job_to_write.score >=min_score:
            database.write_job_to_jobs(conn, job_to_write, created_at)
        else:
            database.write_job_to_discarded(
                conn, 
                job_to_write, 
                f"Score {job_to_write.score} below the minimum threshold of {min_score}", 
                created_at,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        database.delete_from_staging(conn, id)

def drain_staging(conn: sqlite3.Connection, config: dict[str, Any]) -> None:
    while True:
        start_time = time.perf_counter()
        
        row_data = database.get_next_staging(conn)
        if row_data is None:
            break
        process_job_with_llm(conn, config, row_data)
        
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print(f"Processing took {execution_time:.6f}s.\n")

def pipeline():
    config, filters = load_config()
    conn = database.connect()
    try:
        database.init_tables(conn)

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False) # TODO: switch to True when tests are over
            linkedin_scraper(conn, browser, config, filters)
       
        # TODO: deduplicate_staging()
        drain_staging(conn, config)
            
    finally:
        try:
            database.close(conn)
        except sqlite3.Error as error:
            print(f"Error: {error}")