import sqlite3
from joblisting import StagingJobListing
from datetime import datetime

def connect() -> sqlite3.Connection:
    return sqlite3.connect("./data/data.db")

def init_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    user_version = cursor.fetchone()[0]
    
    if  user_version == 0:
        cursor.execute("""
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

        cursor.execute("""
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

        cursor.execute("""
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discarded (
                id INTEGER PRIMARY KEY,

                title TEXT,
                company TEXT,
                location TEXT,
                description TEXT,
                source TEXT,
                job_id TEXT,
                url TEXT,
                
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
                
                UNIQUE(source, job_id)
                UNIQUE(url)
            )
            """)
        conn.commit()
    else:
        raise Exception("Version not found")

def write_job_to_staging(conn: sqlite3.Connection, job: StagingJobListing) -> None:
    cursor = conn.cursor()
    cursor.execute("""
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
    cursor.execute("""
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
    conn.commit()

def get_next_ingest(conn: sqlite3.Connection, source: str) -> None:
    return conn.execute("""
        SELECT * FROM ingest
        WHERE source = ?
        ORDER BY id
        LIMIT 1
        """, 
        (source,)
    ).fetchone()

def delete_ingest(conn: sqlite3.Connection, ingest_id: str) -> None:
    conn.execute("""
        DELETE FROM ingest 
        WHERE id = ?
        """,
        (ingest_id,)
    )
    conn.commit()

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
        LIMIT 1
        """,
        (source, job_id, url,
        source, job_id, url,
        source, job_id, url)
    )
    return cursor.fetchone() is not None

def close(conn: sqlite3.Connection) -> None:
    conn.close()