import sqlite3

def connect() -> sqlite3.Connection:
    return sqlite3.connect("./data/data.db")

def init_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA schema_version")
    schema_version = cursor.fetchone()[0]

    print(schema_version)
    
    if schema_version == 0 or schema_version == 1:
        table_creation_query = """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
    
                status TEXT NOT NULL DEFAULT 'New',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                applied_at TEXT,
                resume_used TEXT,
    
                score INTEGER,
                short_score TEXT,
                reasoning TEXT
            )
            """
    else:
        raise Exception("Version not found")
    cursor.execute(table_creation_query)
    conn.commit()

def close(conn: sqlite3.Connection) -> None:
    conn.close()