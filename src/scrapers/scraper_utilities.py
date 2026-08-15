from tomllib import load
from typing_extensions import Any
from sqlite3 import Connection

with open("config.toml", "rb") as f:
    toml_config = load(f)

company_blacklist = set(toml_config["search"]["companies_to_skip"])

def load_config() -> dict[str, Any]:
    return toml_config

def is_company_blacklisted(company: str) -> bool:
    return company in company_blacklist

def job_exists_in_pipeline(conn: Connection, source: str, job_id: str, canonical_url: str | None = None) -> bool:
    # Check if the job already exists in staging or jobs without the canonical URL
    if not canonical_url:
        cursor = conn.execute("""
            SELECT 1 FROM ingest
                WHERE source = ? AND job_id = ?
            UNION ALL
            SELECT 1 FROM staging
                WHERE source = ? AND job_id = ?
            UNION ALL
            SELECT 1 FROM jobs
                WHERE source = ? AND job_id = ?
            LIMIT 1
            """,
            (source, job_id, source, job_id, source, job_id)
        )
        
    # If canonical_url exists, use it for deduplication
    else:
        cursor = conn.execute("""
            SELECT 1 FROM ingest
                WHERE canonical_url = ?
            UNION ALL
            SELECT 1 FROM staging
                WHERE canonical_url = ?
            UNION ALL
            SELECT 1 FROM jobs
                WHERE canonical_url = ?
            LIMIT 1
            """,
            (canonical_url, canonical_url, canonical_url)
        )
    return cursor.fetchone() is not None