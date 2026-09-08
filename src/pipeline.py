import sqlite3
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from shutil import copyfile
from typing import Any

from rich.text import Text
from tomllib import load

import database
import llm
from scrapers.scraper_utilities import JobEntry, JobFilters, JobStatus

ProgressCallback = Callable[[Text], None]

def load_config(path: str | Path = "config.toml") -> dict[str, Any]:
    """
    Load a TOML config file and return it as a dict.

    Parameters:
    -----
    path (optional): path to the config file.
    
    Returns:
    -----
    dict[str, Any]: the TOML configuration as a dictionary.
    """

    # TODO: add a popup that says that config.example.toml was copied to make config.toml
    path = Path(path)
    if not path.exists():
        example_path = path.with_name("config.example.toml")

        if not example_path.exists():
            raise FileNotFoundError(f"Neither {path} nor {example_path} exists.")
    
        _ = copyfile(example_path, path)
        print(f"Created {path} from {example_path}")
    
    with open(path, "rb") as f:
        return load(f)

def load_filters(config: dict[str, Any]) -> JobFilters:
    """
    Create a JobFilters object from the config.

    
    Parameters:
    -----
    config: reference to a config TOML dict[str, Any].
    
    Returns:
    -----
    JobFilters: object containing blacklisted terms for companies.
    """
    # TODO: delete this in the future, replace with a table in sqlite
    return JobFilters(config)

def process_job_with_llm(conn: sqlite3.Connection, config: dict[str, Any], job: JobEntry, progress_callback: ProgressCallback) -> None:
    """
    Process a job with the LLM and write to the database.

    
    Parameters:
    -----
    conn: connection to the SQLite database.
    config: reference to a config TOML dict[str, Any].
    row: tuple corresponding to a row from staging.
    """

    # TODO: maybe this should be split into two functions?
    min_score = int(config["llm"]["minimum_score"])
    progress_callback(Text(f"Processing job: {job.title}, at {job.company}"))

    job_to_write = llm.use_llm(config, job, progress_callback)
    job_to_write.updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with conn:
        if job_to_write.score is not None and job_to_write.score >= min_score:
            job_to_write.status = JobStatus.PENDING_MANUAL_REVIEW
            database.write_job_to_jobs(conn, job_to_write)
        else:
            job_to_write.status = JobStatus.DISCARDED
            job_to_write.discard_reason = f"Score {job_to_write.score} below the minimum threshold of {min_score}"
            database.write_job_to_discarded(conn, job_to_write)
        database.delete_from_staging(conn, job_to_write)


def drain_staging(conn: sqlite3.Connection, config: dict[str, Any], progress_callback: ProgressCallback) -> None:
    """
    Drains jobs from staging and sends them to the LLM.

    
    Parameters:
    -----
    conn: connection to the SQLite database.
    config: reference to a config TOML dict[str, Any].
    """
    progress_callback(Text("Draining staging table and processing with LLM...", style = "#f52bfb"))
    offset = 0
    while True:
        start_time = time.perf_counter()

        try:
            job = database.get_next_staging(conn, offset)
            if job is None:
                break
            process_job_with_llm(conn, config, job, progress_callback)    
        except llm.LLMProcessingError as error:
            progress_callback(Text(str(error)))
            offset += 1

        end_time = time.perf_counter()
        execution_time = end_time - start_time
        progress_callback(Text(f"Processing took {execution_time:.6f}s.\n"))