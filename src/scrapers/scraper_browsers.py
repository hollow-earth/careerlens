from contextlib import contextmanager
from enum import Enum, auto

from playwright.sync_api import sync_playwright

from scrapers.indeed import indeed_scraper
from scrapers.linkedin import linkedin_scraper


class Browsers(Enum):
    PLAYWRIGHT_FIREFOX = auto()
    PLAYWRIGHT_CHROMIUM = auto()
    PLAYWRIGHT_FIREFOX_CONTEXT = auto()

class ScraperSources(Enum):
    LINKEDIN = auto()
    INDEED = auto()

# ScraperSources enum: function from scrapers.module, requires_browser
SCRAPERS = {
    ScraperSources.LINKEDIN: (linkedin_scraper, Browsers.PLAYWRIGHT_FIREFOX),
    ScraperSources.INDEED: (indeed_scraper, Browsers.PLAYWRIGHT_FIREFOX_CONTEXT)
}

@contextmanager
def browser_context(browser_type: Browsers):
    if browser_type is Browsers.PLAYWRIGHT_FIREFOX:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False)
            page = browser.new_page()
            yield page
            browser.close()

    elif browser_type is Browsers.PLAYWRIGHT_CHROMIUM:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            yield page
            browser.close()

    elif browser_type is Browsers.PLAYWRIGHT_FIREFOX_CONTEXT:
        with sync_playwright() as p:
            context = p.firefox.launch_persistent_context(
                user_data_dir="./.playwright-profile",
                headless=False,
            )
            context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            """)

            page = context.pages[0]
            yield page
            context.close()
    