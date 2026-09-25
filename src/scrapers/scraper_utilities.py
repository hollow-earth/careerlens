import re
import unicodedata
from contextlib import contextmanager
from dataclasses import InitVar, dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from tkinter import Tk, filedialog
from typing import Any

from playwright.sync_api import sync_playwright

from src.scrapers.indeed import indeed_scraper
from src.scrapers.linkedin import linkedin_scraper
from camoufox import Camoufox


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )

class JobFilters:
    def __init__(self, config: dict[str, Any]) -> None:
        self.term_blacklist = {normalize(term) for term in config["search"]["blacklisted_terms"]}
        self.excluded_pattern = re.compile(r"\b(?:" + "|".join(re.escape(term) for term in self.term_blacklist) + r")\b")

    def is_title_blacklisted(self, title: str) -> bool:
        return self.excluded_pattern.search(normalize(title)) is not None

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

class JobSource(Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    EIGHTFOLD = "eightfold"
    SMARTRECRUITERS = "smart_recruiters"
    ASHBY = "ashby"
    GREENHOUSE = "greenhouse"
    BAMBOO_HR = "bamboo_hr"
    ICIMS = "icims"
    LEVER = "lever"
    WORKDAY = "workday"

class JobStatus(Enum):
    PENDING = "pending"                             # Staging: after scraping filled in the info
    DUPLICATE_REVIEW = "duplicate_review"           # Staging: candidate for deduplication
    READY = "ready"                                 # Staging: ready for LLM consumption
    PENDING_MANUAL_REVIEW = "pending_manual_review" # Jobs: ready for manual review (apply or discard)
    APPLIED = "applied"                             # Jobs: self-explanatory
    DISCARDED = "discarded"                         # Discarded: self-explanatory

class CompanyTrustStatus(Enum):
    TRUSTED = "trusted"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"

@dataclass 
class JobEntry:
    source: JobSource
    job_id: str
    url: str

    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    status: JobStatus | None = None
    resume_used: str | None = None
    score: int | None = None
    short_score: str | None = None
    reasoning: str | None = None
    created_at: str | datetime | None = None
    updated_at: str | datetime | None = None
    applied_at: str | datetime | None = None
    discarded_at: str | datetime | None = None
    discard_reason: str | None = None

    def __post_init__(self):
        if not self.source:
            raise ValueError("source must be a non-empty str")
        if not self.job_id:
            raise ValueError("job_id must be a non-empty str")
        if not self.url:
            raise ValueError("url must be a non-empty str")

@dataclass
class CompanyEntry:
    name_input: InitVar[str]

    trust_status: CompanyTrustStatus = CompanyTrustStatus.UNKNOWN
    normalized_name: str = ""
    
    def __post_init__(self, name_input: str):
        self.normalized_name = normalize(name_input)

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