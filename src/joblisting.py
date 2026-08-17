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

    status: str # pending, duplicate_review, duplicate, ready
    scraped_at: str

class JobListing(StagingJobListing):
    ...