from random import randint
from sqlite3.dbapi2 import Connection

from src import database
from src.scrapers.scraper_utilities import JobEntry, JobSource

POPULATE_NUMBER_ENTRIES = 25

"""

Tests with the ingest table

"""


def helper_populate_ingest_entries(conn: Connection) -> set[int]:
    s: set[int] = set()
    i = 0
    while i < POPULATE_NUMBER_ENTRIES:
        id = randint(1, 999999)
        if id not in s:
            s.add(id)
            i += 1
            database.write_job_to_ingest(
                conn,
                JobEntry(JobSource.LINKEDIN, f"{id}", f"https://linkedin.com/{id}"),
            )
    return s


def test_ingest_insert(conn: Connection):
    s = helper_populate_ingest_entries(conn)
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == len(s)


def test_ingest_dedups_on_url(conn: Connection):
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789")
    job2 = JobEntry(JobSource.LINKEDIN, "555555555", "https://linkedin.com/123456789")
    database.write_job_to_ingest(conn, job1)
    database.write_job_to_ingest(conn, job2)
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == 1


def test_ingest_dedups_on_job_id(conn: Connection):
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789")
    job2 = JobEntry(JobSource.LINKEDIN, "555555555", "https://linkedin.com/123456789")
    database.write_job_to_ingest(conn, job1)
    database.write_job_to_ingest(conn, job2)
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == 1


def test_ingest_dedups_on_rescrape(conn: Connection):
    job = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789")
    for _ in range(5):
        database.write_job_to_ingest(conn, job)
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == 1


def test_ingest_delete(conn: Connection):
    s = helper_populate_ingest_entries(conn)
    N = randint(1, POPULATE_NUMBER_ENTRIES - 1)
    for _ in range(N):
        id = s.pop()
        database.delete_from_ingest(
            conn,
            JobEntry(JobSource.LINKEDIN, f"{id}", f"https://linkedin.com/{id}")
        )
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == len(s)