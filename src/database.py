import sqlite3
from datetime import datetime

from joblisting import StagingJobListing


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
                scraped_at TEXT NOT NULL,
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
        conn.commit()

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
                scraped_at TEXT NOT NULL,
                created_at TEXT NOT NULL,

                UNIQUE(source, job_id)
                UNIQUE(url)
            )
            """)
        conn.commit()

        _ = cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingest (
                id INTEGER PRIMARY KEY,
                
                source TEXT NOT NULL,
                job_id TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,

                scraped_at TEXT NOT NULL,

                UNIQUE(source, job_id)
                UNIQUE(url)
            )
            """)
        conn.commit()

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
                scraped_at TEXT,
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
        conn.commit()
    else:
        raise Exception("Version not found")

def write_job_to_staging(conn: sqlite3.Connection, job: StagingJobListing) -> None:
    cursor = conn.cursor()
    _ = cursor.execute("""
            INSERT OR IGNORE INTO staging 
            (title, company, location, description, source, job_id, url, status, scraped_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.title,
            job.company,
            job.location,
            job.description,
            job.source,
            job.job_id,
            job.url,
            job.status,
            job.scraped_at,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    )

def write_job_to_ingest(conn: sqlite3.Connection, source: str, job_id: str, url: str) -> None:
    cursor = conn.cursor()
    _ = cursor.execute("""
            INSERT OR IGNORE INTO ingest 
            (source, job_id, url, scraped_at) 
            VALUES (?, ?, ?, ?)
        """,
        (
            source, 
            job_id, 
            url, 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    )

def write_job_to_discarded(conn: sqlite3.Connection, 
        source: str, job_id: str, url: str, discard_reason: str,
        title: str | None = None, company: str | None = None, location: str | None = None, description: str | None = None,
        status: str | None = None, scraped_at: str | None = None, created_at: str | None = None,
        updated_at: str | None = None, applied_at: str | None = None, resume_used: str | None = None,
        score: int | None = None, short_score: str | None = None, reasoning: str | None = None
    ) -> None:
    cursor = conn.cursor()
    _ = cursor.execute("""
            INSERT OR IGNORE INTO discarded 
            (source, job_id, url, discard_reason, discarded_at,
            title, company, location, description, 
            status, scraped_at, created_at, 
            updated_at, applied_at, resume_used, 
            score, short_score, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source,
            job_id,
            url,
            discard_reason,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            title,
            company,
            location,
            description,
            status,
            scraped_at,
            created_at,
            updated_at,
            applied_at,
            resume_used,
            score,
            short_score,
            reasoning,
        )
    )

def get_next_ingest(conn: sqlite3.Connection, source: str) -> sqlite3.Row | None:
    return conn.execute("""
        SELECT * FROM ingest
        WHERE source = ?
        ORDER BY id
        LIMIT 1
        """, 
        (source,)
    ).fetchone()

def delete_from_ingest(conn: sqlite3.Connection, ingest_id: str) -> None:
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

def close(conn: sqlite3.Connection) -> None:
    conn.close()