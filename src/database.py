import sqlite3
from joblisting import JobListing
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
                url TEXT NOT NULL UNIQUE,
                redirects_to TEXT,
                
                status TEXT NOT NULL DEFAULT 'New',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                applied_at TEXT,
                resume_used TEXT,
    
                score INTEGER,
                short_score TEXT,
                reasoning TEXT,

                UNIQUE(source, job_id, url)
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
                url TEXT NOT NULL UNIQUE,
                redirects_to TEXT,

                created_at TEXT NOT NULL,

                UNIQUE(source, job_id, url)
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

                UNIQUE(source, job_id, url)
            )
            """)
        conn.commit()
    else:
        raise Exception("Version not found")

def write_job_to_staging(conn: sqlite3.Connection, job: JobListing) -> None:
    cursor = conn.cursor()
    cursor.execute("""
            INSERT OR IGNORE INTO staging 
            (id, title, company, description, location, source, link)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.job_id, 
            job.title, 
            job.company, 
            job.description, 
            job.location, 
            job.source, 
            job.url
        )
    )
    conn.commit()

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

def close(conn: sqlite3.Connection) -> None:
    conn.close()