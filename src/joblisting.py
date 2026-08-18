from dataclasses import dataclass


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