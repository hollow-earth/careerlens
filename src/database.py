import sqlite3
from joblisting import JobListing

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
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                redirects_to TEXT NOT NULL,
                
                status TEXT NOT NULL DEFAULT 'New',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                applied_at TEXT,
                resume_used TEXT,
    
                score INTEGER,
                short_score TEXT,
                reasoning TEXT
            )
            """)
        conn.commit()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staging (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE
                redirects_to TEXT NOT NULL
            )
            """)
        conn.commit()
    else:
        raise Exception("Version not found")

def write_job_to_staging(conn: sqlite3.Connection, job: JobListing) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO staging 
            (id, title, company, description, location, source, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.job_id, 
            job.title, 
            job.company, 
            job.description, 
            job.location, 
            job.source, 
            job.link)
        )
    conn.commit()

def close(conn: sqlite3.Connection) -> None:
    conn.close()