from dataclasses import dataclass

@dataclass
class JobListing:
    job_id: int
    title: str
    link: str
    company: str
    location: str
    description: str