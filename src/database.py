import sqlite3
from datetime import datetime

from scrapers.scraper_utilities import JobListing, JobData, JobStatus


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect("./data/data.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    user_version = cursor.fetchone()[0]
    
    if  user_version == 0:
        _ = cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,

                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                source TEXT NOT NULL,
                job_id TEXT NOT NULL,
                url TEXT NOT NULL,
                
                status TEXT NOT NULL DEFAULT 'New',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                applied_at TEXT,
                resume_used TEXT,
    
                score INTEGER,
                short_score TEXT,
                reasoning TEXT,

                UNIQUE(source, job_id)
                UNIQUE(url)
            )
            """)

        _ = cursor.execute("""
            CREATE TABLE IF NOT EXISTS staging (
                id INTEGER PRIMARY KEY,

                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                source TEXT NOT NULL,
                job_id TEXT NOT NULL,
                url TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,

                UNIQUE(source, job_id)
                UNIQUE(url)
            )
            """)

        _ = cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingest (
                id INTEGER PRIMARY KEY,
                
                source TEXT NOT NULL,
                job_id TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,

                UNIQUE(source, job_id)
                UNIQUE(url)
            )
            """)

        _ = cursor.execute("""
            CREATE TABLE IF NOT EXISTS discarded (
                id INTEGER PRIMARY KEY,

                title TEXT,
                company TEXT,
                location TEXT,
                description TEXT,
                source TEXT NOT NULL,
                job_id TEXT NOT NULL,
                url TEXT NOT NULL,
                
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                applied_at TEXT,
                resume_used TEXT,
    
                score INTEGER,
                short_score TEXT,
                reasoning TEXT,

                discard_reason TEXT NOT NULL,
                discarded_at TEXT NOT NULL,
                
                UNIQUE(source, job_id)
                UNIQUE(url)
            )
            """)

        _ = cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                normalized_name TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'unknown'
            )
            """)
        conn.commit()
    else:
        raise Exception("Version not found")

def write_job_to_staging(conn: sqlite3.Connection, job: JobData) -> None:
    cursor = conn.cursor()
    _ = cursor.execute("""
            INSERT OR IGNORE INTO staging 
            (title, company, location, description, source, job_id, url, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.title,
            job.company,
            job.location,
            job.description,
            job.source,
            job.job_id,
            job.url,
            JobStatus.PENDING.value,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    )

def write_job_to_ingest(conn: sqlite3.Connection, source: str, job_id: str, url: str) -> None:
    cursor = conn.cursor()
    _ = cursor.execute("""
            INSERT OR IGNORE INTO ingest 
            (source, job_id, url) 
            VALUES (?, ?, ?)
        """,
        (
            source, 
            job_id, 
            url
        )
    )

def write_job_to_discarded(conn: sqlite3.Connection, job: JobData, discard_reason: str, 
    created_at: str, updated_at: str | None = None, applied_at: str | None = None) -> None:
    if isinstance(job, JobListing):
        resume_used = job.resume_used
        score = job.score
        short_score = job.short_score
        reasoning = job.reasoning
    else:
        resume_used = None
        score = None
        short_score = None
        reasoning = None

    cursor = conn.cursor()
    _ = cursor.execute("""
            INSERT OR IGNORE INTO discarded 
            (
            title, company, location, description, source, job_id, url,
            status, created_at, updated_at, applied_at, resume_used, 
            score, short_score, reasoning,
            discard_reason, discarded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.title,
            job.company,
            job.location,
            job.description,
            job.source,
            job.job_id,
            job.url,
            JobStatus.DISCARDED.value,
            created_at,
            updated_at,
            applied_at,
            resume_used,
            score,
            short_score,
            reasoning,
            discard_reason,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    )

# TODO: change this to return a tuple instead of a sqlite3.Row
def get_next_ingest(conn: sqlite3.Connection, source: str) -> sqlite3.Row | None:
    return conn.execute("""
        SELECT * FROM ingest
        WHERE source = ?
        ORDER BY id
        LIMIT 1
        """, 
        (source,)
    ).fetchone()

def delete_from_ingest(conn: sqlite3.Connection, ingest_id: int) -> None:
    conn.execute("""
        DELETE FROM ingest 
        WHERE id = ?
        """,
        (ingest_id,)
    )

def job_exists_in_pipeline(conn: sqlite3.Connection, source: str, job_id: str, url: str) -> bool:
    cursor = conn.execute("""
        SELECT 1 FROM ingest
            WHERE (source = ? AND job_id = ?) OR url = ?
        UNION ALL
        SELECT 1 FROM staging
            WHERE (source = ? AND job_id = ?) OR url = ?
        UNION ALL
        SELECT 1 FROM jobs
            WHERE (source = ? AND job_id = ?) OR url = ?
        UNION ALL
        SELECT 1 FROM discarded
            WHERE (source = ? AND job_id = ?) OR url = ?
        LIMIT 1
        """,
        (source, job_id, url,
        source, job_id, url,
        source, job_id, url,
        source, job_id, url)
    )
    return cursor.fetchone() is not None

def get_next_staging(conn: sqlite3.Connection) -> tuple[int, JobData, str] | None:
    row =  conn.execute("""
        SELECT * FROM staging
        WHERE status = ?
        ORDER BY id
        LIMIT 1
        """,
        (JobStatus.READY.value, )
    ).fetchone()

    if row is None:
        return None

    job = JobData(
        title = row["title"],
        company = row["company"],
        location = row["location"],
        description = row["description"],
        source = row["source"],
        job_id = row["job_id"],
        url = row["url"],
        status = JobStatus(row["status"])
    )
    return (row["id"], job, row["created_at"])

def delete_from_staging(conn: sqlite3.Connection, staging_id: int) -> None:
    conn.execute("""
        DELETE FROM staging 
        WHERE id = ?
        """,
        (staging_id,)
    )

def write_job_to_jobs(conn: sqlite3.Connection, job: JobListing, created_at: str) -> None:
    cursor = conn.cursor()
    _ = cursor.execute("""
            INSERT OR IGNORE INTO jobs 
            (title, company, location, description, source, job_id, url, status, created_at,
            updated_at, applied_at, resume_used, score, short_score, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.title,
            job.company,
            job.location,
            job.description,
            job.source,
            job.job_id,
            job.url,
            JobStatus.PENDING_MANUAL_REVIEW.value,
            created_at,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
            None,
            None,
            job.score,
            job.short_score,
            job.reasoning
        )
    )

def close(conn: sqlite3.Connection) -> None:
    conn.close()
