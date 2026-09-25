from contextlib import contextmanager
from enum import Enum, auto

from camoufox.sync_api import Camoufox
from playwright.sync_api import sync_playwright

from scrapers.indeed import indeed_scraper
from scrapers.linkedin import linkedin_scraper


class Browsers(Enum):
    CAMOUFOX = auto()
    PLAYWRIGHT_FIREFOX = auto()
    PLAYWRIGHT_CHROMIUM = auto()

class ScraperSources(Enum):
    LINKEDIN = auto()
    INDEED = auto()

# ScraperSources enum: function from scrapers.module, requires_browser
SCRAPERS = {
    ScraperSources.LINKEDIN: (linkedin_scraper, Browsers.PLAYWRIGHT_FIREFOX),
    ScraperSources.INDEED: (indeed_scraper, Browsers.CAMOUFOX)
}

@contextmanager
def browser_context(browser_type: Browsers):
    if browser_type is Browsers.PLAYWRIGHT_FIREFOX:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            yield browser

    elif browser_type is Browsers.PLAYWRIGHT_CHROMIUM:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser

    elif browser_type is Browsers.CAMOUFOX:
        with Camoufox(headless=True) as browser:
            yield browser