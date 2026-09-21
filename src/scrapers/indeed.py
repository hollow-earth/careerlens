from collections.abc import Callable
from random import uniform
from sqlite3 import Connection

from playwright.sync_api import Browser
from rich.text import Text

from scrapers.scraper_utilities import JobFilters

PAGE_DELAY = uniform(3.0, 5.0)
MAX_RETRIES = 3
ProgressCallback = Callable[[Text], None]

def indeed_extract_url_contents(conn: Connection, browser: Browser, filters:JobFilters, progress_callback: ProgressCallback) -> None:
    ...

def indeed_scraper(conn: Connection, config: dict[str, object], filters: JobFilters, browser: Browser, callback: ProgressCallback) -> None:
    callback(Text("Extracting Indeed job contents...", style="#f52bfb"))
    indeed_extract_url_contents(conn, browser, filters, callback)
    callback(Text("Finished extracting Indeed job contents.", style="#f52bfb"))