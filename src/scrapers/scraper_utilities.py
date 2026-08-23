import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing_extensions import Any


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )

class JobFilters:
    def __init__(self, config: dict[str, Any]) -> None:
        self.term_blacklist = {normalize(term) for term in config["search"]["blacklisted_terms"]}
        self.excluded_pattern = re.compile(r"\b(?:" + "|".join(re.escape(term) for term in self.term_blacklist) + r")\b")
        
        self.company_blacklist = {normalize(company) for company in config["search"]["blacklisted_companies"]}

    def is_title_blacklisted(self, title: str) -> bool:
        return self.excluded_pattern.search(normalize(title)) is not None
    
    def is_company_blacklisted(self, company: str) -> bool:
        return company.lower() in self.company_blacklist

class JobSource(Enum):
    LINKEDIN = "linkedin"

class JobStatus(Enum):
    PENDING = "pending"                             # Staging: after scraping filled in the info
    DUPLICATE_REVIEW = "duplicate_review"           # Staging: candidate for deduplication
    READY = "ready"                                 # Staging: ready for LLM consumption
    PENDING_MANUAL_REVIEW = "pending_manual_review" # Jobs: ready for manual review (apply or discard)
    APPLIED = "applied"                             # Jobs: self-explanatory
    DISCARDED = "discarded"                         # Discarded: self-explanatory

@dataclass 
class JobEntry:
    source: JobSource
    job_id: str
    url: str

    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    status: JobStatus = JobStatus.PENDING
    resume_used: str | None = None
    score: int | None = None
    short_score: str | None = None
    reasoning: str | None = None
    created_at: str | datetime | None = None
    updated_at: str | datetime | None = None
    applied_at: str | datetime | None = None
    discarded_at: str | datetime | None = None
    discard_reason: str | None = None