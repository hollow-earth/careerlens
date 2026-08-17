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

def job_exists_in_pipeline(conn: Connection, source: str, job_id: str, url: str) -> bool:
    cursor = conn.execute("""
        SELECT 1 FROM ingest
            WHERE (source = ? AND job_id = ?) OR url = ?
        UNION ALL
        SELECT 1 FROM staging
            WHERE (source = ? AND job_id = ?) OR url = ?
        UNION ALL
        SELECT 1 FROM jobs
            WHERE (source = ? AND job_id = ?) OR url = ?
        LIMIT 1
        """,
        (source, job_id, url,
        source, job_id, url,
        source, job_id, url)
    )
    return cursor.fetchone() is not None

def get_next_ingest(conn, source):
    return conn.execute("""
        SELECT * FROM ingest
        WHERE source = ?
        ORDER BY id
        LIMIT 1
        """, 
        (source,)
    ).fetchone()

def delete_ingest(conn, ingest_id):
    conn.execute("""
        DELETE FROM ingest 
        WHERE id = ?
        """,
        (ingest_id,)
    )
    conn.commit()