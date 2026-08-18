import re
import unicodedata
from dataclasses import dataclass

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

@dataclass
class StagingJobListing:
    title: str
    company: str
    location: str
    description: str
    source: str
    job_id: str
    url: str

    status: str # pending, duplicate_review, ready
    scraped_at: str

@dataclass
class JobListing(StagingJobListing):
    created_at: str
    updated_at: str | None
    applied_at: str | None
    resume_used: str | None
    score: int
    short_score: str
    reasoning: str