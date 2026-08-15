from dataclasses import dataclass

@dataclass
class JobListing:
    job_id: int
    title: str
    company: str
    description: str
    location: str
    source: str
    url: str