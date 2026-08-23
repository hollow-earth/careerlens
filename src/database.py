import sqlite3
from datetime import datetime, timezone

from scrapers.scraper_utilities import JobEntry, JobSource, JobStatus

INGEST_REQUIRED = ("source", "job_id", "url")
STAGING_REQUIRED = INGEST_REQUIRED + ("title", "company", "location", "description", "status")
JOBS_REQUIRED = STAGING_REQUIRED + ("created_at", "score", "short_score", "reasoning")
DISCARDED_REQUIRED = STAGING_REQUIRED + ("discard_reason", )

def connect() -> sqlite3.Connection:
    """
    Connect to the CareerLens SQLite database.

    Returns:
    ------
    sqlite3.Connection: An open database connection.
    """
    
    try:
        conn = sqlite3.connect("./data/data.db")
    except sqlite3.Error as error:
        raise Exception(f"Error: {error}")
    else:
        conn.row_factory = sqlite3.Row
        return conn


def close(conn: sqlite3.Connection) -> None:
    conn.close()


def init_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    user_version = cursor.fetchone()[0]
    
    if  user_version == 0:
        _ = cursor.executescript("""
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
                reasoning TEXT
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source_jobid ON jobs(source, job_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);
            """)

        _ = cursor.executescript("""
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
                created_at TEXT NOT NULL
            );
            
            CREATE UNIQUE INDEX IF NOT EXISTS idx_staging_source_jobid ON staging(source, job_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_staging_url ON staging(url);
            """)

        _ = cursor.executescript("""
            CREATE TABLE IF NOT EXISTS ingest (
                id INTEGER PRIMARY KEY,
                
                source TEXT NOT NULL,
                job_id TEXT NOT NULL,
                url TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_ingest_source_jobid ON ingest(source, job_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ingest_url ON ingest(url);
            """)

        _ = cursor.executescript("""
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
                discarded_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_discarded_source_jobid ON discarded(source, job_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_discarded_url ON discarded(url);
            """)

        _ = cursor.executescript("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                normalized_name TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'unknown',
                requires_cover_letter BOOLEAN
            );
            """)
        conn.commit()
    else:
        raise Exception("Version not found")


def require_fields(job: JobEntry, fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if getattr(job, field) is None]
    if missing:
        raise ValueError(f"JobEntry missing required fields: {', '.join(missing)}")


def job_exists_in_pipeline(conn: sqlite3.Connection, job: JobEntry) -> bool:
    require_fields(job, INGEST_REQUIRED)
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
        (job.source.value, job.job_id, job.url,
        job.source.value, job.job_id, job.url,
        job.source.value, job.job_id, job.url,
        job.source.value, job.job_id, job.url)
    )
    return cursor.fetchone() is not None


def write_job_to_ingest(conn: sqlite3.Connection, job: JobEntry) -> None:
    require_fields(job, INGEST_REQUIRED)
    cursor = conn.cursor()
    _ = cursor.execute("""
            INSERT OR IGNORE INTO ingest 
            (source, job_id, url) 
            VALUES (?, ?, ?)
        """,
        (
            job.source.value, 
            job.job_id, 
            job.url
        )
    )


def write_job_to_staging(conn: sqlite3.Connection, job: JobEntry) -> None:
    require_fields(job, STAGING_REQUIRED)
    _ = conn.execute("""
            INSERT OR IGNORE INTO staging 
            (title, company, location, description, source, job_id, url, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.title,
            job.company,
            job.location,
            job.description,
            job.source.value,
            job.job_id,
            job.url,
            JobStatus.PENDING.value,
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    )


def write_job_to_discarded(conn: sqlite3.Connection, job: JobEntry) -> None:
    require_fields(job, DISCARDED_REQUIRED)
    cursor = conn.cursor()
    _ = cursor.execute("""
            INSERT OR IGNORE INTO discarded 
            (
            title, company, location, description, source, job_id, url,
            status, created_at, updated_at, applied_at, resume_used, 
            score, short_score, reasoning, discard_reason, discarded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.title,
            job.company,
            job.location,
            job.description,
            job.source.value,
            job.job_id,
            job.url,
            job.status.value,
            job.created_at,
            job.updated_at,
            job.applied_at,
            job.resume_used,
            job.score,
            job.short_score,
            job.reasoning,
            job.discard_reason,
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    )


def write_job_to_jobs(conn: sqlite3.Connection, job: JobEntry) -> None:
    require_fields(job, JOBS_REQUIRED)
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
            job.source.value,
            job.job_id,
            job.url,
            JobStatus.PENDING_MANUAL_REVIEW.value,
            job.created_at,
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            None,
            None,
            job.score,
            job.short_score,
            job.reasoning
        )
    )


def get_next_ingest(conn: sqlite3.Connection, source: JobSource) -> JobEntry | None:
    row = conn.execute("""
        SELECT * FROM ingest
        WHERE source = ?
        ORDER BY id
        LIMIT 1
        """, 
        (source.value,)
    ).fetchone()

    return None if row is None else JobEntry(
        source = JobSource(row["source"]), 
        job_id = row["job_id"], 
        url = row["url"]
    )


def get_next_staging(conn: sqlite3.Connection) -> JobEntry | None:
    row = conn.execute("""
        SELECT * FROM staging
        WHERE status = ?
        ORDER BY id
        LIMIT 1
        """,
        (JobStatus.READY.value, )
    ).fetchone()

    return None if row is None else JobEntry(
        title = row["title"],
        company = row["company"],
        location = row["location"],
        description = row["description"],
        source = row["source"],
        job_id = row["job_id"],
        url = row["url"],
        status = JobStatus(row["status"]),
        created_at = row["created_at"]
    )


def delete_from_ingest(conn: sqlite3.Connection, job: JobEntry) -> None:
    require_fields(job, INGEST_REQUIRED)
    _ = conn.execute("""
        DELETE FROM ingest 
        WHERE (source = ? AND job_id = ?) OR url = ?
        """,
        (job.source.value, job.job_id, job.url,)
    )


def delete_from_staging(conn: sqlite3.Connection, job: JobEntry) -> None:
    require_fields(job, INGEST_REQUIRED)
    _ = conn.execute("""
        DELETE FROM staging 
        WHERE (source = ? AND job_id = ?) OR url = ?
        """,
        (job.source.value, job.job_id, job.url,)
    )
