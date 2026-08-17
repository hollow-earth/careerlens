from dataclasses import dataclass

@dataclass
class JobListing:
    title: str
    company: str
    location: str
    description: str
    source: str
    job_id: str
    url: str