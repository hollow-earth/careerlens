from random import randint
from sqlite3.dbapi2 import Connection

from src import database
from src.scrapers.scraper_utilities import JobEntry, JobSource

POPULATE_NUMBER_ENTRIES = 25

"""
# ========================================= #
# 
#       Tests with the ingest table
# 
# ========================================= #
"""

def helper_populate_ingest_entries(conn: Connection, source: JobSource, number: int) -> set[int]:
    s: set[int] = set()
    i = 0
    while i < number:
        id = randint(1, 999999)
        if id not in s:
            s.add(id)
            i += 1
            job = JobEntry(source, f"{id}", f"https://linkedin.com/{id}")
            database.write_job_to_ingest(conn, job)
            database.require_fields(job, database.INGEST_REQUIRED)
    return s


def test_ingest_insert(conn: Connection) -> None:
    s = helper_populate_ingest_entries(conn, JobSource.LINKEDIN, POPULATE_NUMBER_ENTRIES)
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == len(s)


def test_ingest_dedups_on_url(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789")
    job2 = JobEntry(JobSource.LINKEDIN, "555555555", "https://linkedin.com/123456789")
    database.write_job_to_ingest(conn, job1)
    database.write_job_to_ingest(conn, job2)
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == 1


def test_ingest_dedups_on_job_id(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789")
    job2 = JobEntry(JobSource.LINKEDIN, "555555555", "https://linkedin.com/123456789")
    database.write_job_to_ingest(conn, job1)
    database.write_job_to_ingest(conn, job2)
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == 1


def test_ingest_dedups_on_rescrape(conn: Connection) -> None:
    job = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789")
    for _ in range(5):
        database.write_job_to_ingest(conn, job)
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == 1


def test_ingest_delete(conn: Connection) -> None:
    s = helper_populate_ingest_entries(conn, JobSource.LINKEDIN, POPULATE_NUMBER_ENTRIES)
    N = randint(1, POPULATE_NUMBER_ENTRIES - 1)
    for _ in range(N):
        id = s.pop()
        database.delete_from_ingest(
            conn,
            JobEntry(JobSource.LINKEDIN, f"{id}", f"https://linkedin.com/{id}")
        )
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == len(s)


def test_ingest_get_next(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789")
    job2 = JobEntry(JobSource.INDEED, "a7a3467cad7fdedb", "https://indeed.com/viewjob?jk=a7a3467cad7fdedb")
    job3 = JobEntry(JobSource.LINKEDIN, "555555555", "https://linkedin.com/555555555")
    job4 = JobEntry(JobSource.INDEED, "84ea4a111369c8d7", "https://indeed.com/viewjob?jk=84ea4a111369c8d7")
    job5 = JobEntry(JobSource.LINKEDIN, "555555555", "https://linkedin.com/555555555")
    database.write_job_to_ingest(conn, job1)
    database.write_job_to_ingest(conn, job2)
    database.write_job_to_ingest(conn, job3)
    database.write_job_to_ingest(conn, job4)

    d = database.get_next_ingest(conn, JobSource.LINKEDIN)
    assert d is not None and d.job_id == job1.job_id
    d = database.get_next_ingest(conn, JobSource.LINKEDIN)
    assert d is not None and d.job_id == job1.job_id
    d = database.get_next_ingest(conn, JobSource.LINKEDIN)
    assert d is not None and d.job_id == job1.job_id
    database.delete_from_ingest(conn, job1)

    d = database.get_next_ingest(conn, JobSource.LINKEDIN)
    assert d is not None and d.job_id == job3.job_id
    database.delete_from_ingest(conn, job3)

    database.write_job_to_ingest(conn, job5)

    d = database.get_next_ingest(conn, JobSource.INDEED)
    assert d is not None and d.job_id == job2.job_id
    database.delete_from_ingest(conn, job2)
    
    d = database.get_next_ingest(conn, JobSource.INDEED)
    assert d is not None and d.job_id == job4.job_id
    database.delete_from_ingest(conn, job4)

    d = database.get_next_ingest(conn, JobSource.LINKEDIN)
    assert d is not None and d.job_id == job5.job_id
    database.delete_from_ingest(conn, job5)

    assert database.get_next_ingest(conn, JobSource.LINKEDIN) is None
    assert database.get_next_ingest(conn, JobSource.INDEED) is None


def test_ingest_exists_in_pipeline(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789")
    job2 = JobEntry(JobSource.INDEED, "a7a3467cad7fdedb", "https://indeed.com/viewjob?jk=a7a3467cad7fdedb")
    database.write_job_to_ingest(conn, job1)
    assert database.job_exists_in_pipeline(conn, job1) is True
    assert database.job_exists_in_pipeline(conn, job2) is False


"""
# ========================================= #
# 
#       Tests with the staging table
# 
# ========================================= #
"""

def helper_populate_staging_entries(conn: Connection, source: JobSource, number: int) -> set[int]:
    s: set[int] = set()
    i = 0
    while i < number:
        id = randint(1, 999999)
        if id not in s:
            s.add(id)
            i += 1
            job = JobEntry(source, f"{id}", f"https://linkedin.com/{id}",
                f"SomeTitle{id}", f"SomeCompany{id}", f"SomeLocation{id}", f"SomeDescription{id}")
            database.write_job_to_staging(conn, job)
            database.require_fields(job, database.STAGING_REQUIRED)
    return s


def test_staging_insert(conn: Connection) -> None:
    s = helper_populate_staging_entries(conn, JobSource.LINKEDIN, POPULATE_NUMBER_ENTRIES)
    res = conn.execute("SELECT * FROM staging").fetchall()
    assert len(res) == len(s)


def test_staging_dedups_on_url(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription")
    job2 = JobEntry(JobSource.LINKEDIN, "555555555", "https://linkedin.com/123456789",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription")
    database.write_job_to_staging(conn, job1)
    database.write_job_to_staging(conn, job2)
    res = conn.execute("SELECT * FROM staging").fetchall()
    assert len(res) == 1


def test_staging_dedups_on_job_id(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription")
    job2 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/555555555",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription")
    database.write_job_to_staging(conn, job1)
    database.write_job_to_staging(conn, job2)
    res = conn.execute("SELECT * FROM staging").fetchall()
    assert len(res) == 1


def test_staging_delete(conn: Connection) -> None:
    s = helper_populate_staging_entries(conn, JobSource.LINKEDIN, POPULATE_NUMBER_ENTRIES)
    N = randint(1, POPULATE_NUMBER_ENTRIES - 1)
    for _ in range(N):
        id = s.pop()
        database.delete_from_staging(
            conn,
            JobEntry(JobSource.LINKEDIN, f"{id}", f"https://linkedin.com/{id}",
                f"SomeTitle{id}", f"SomeCompany{id}", f"SomeLocation{id}", f"SomeDescription{id}")
        )
    res = conn.execute("SELECT * FROM ingest").fetchall()
    assert len(res) == len(s)


def test_staging_get_next(conn: Connection) -> None:
    ...


def test_staging_exists_in_pipeline(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription")
    job2 = JobEntry(JobSource.INDEED, "a7a3467cad7fdedb", "https://indeed.com/viewjob?jk=a7a3467cad7fdedb",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription")
    database.write_job_to_staging(conn, job1)
    assert database.job_exists_in_pipeline(conn, job1) is True
    assert database.job_exists_in_pipeline(conn, job2) is False


"""
# ========================================= #
# 
#       Tests with the jobs table
# 
# ========================================= #
"""





"""
# ========================================= #
# 
#       Tests with the discarded table
# 
# ========================================= #
"""





"""
# ========================================= #
# 
#       Tests with the companies table
# 
# ========================================= #
"""





"""
# ========================================= #
# 
#       Tests with deduplication
# 
# ========================================= #
"""

# def job_exists_in_pipeline(conn: sqlite3.Connection, job: JobEntry) -> bool:




"""
def write_job_to_staging(conn: sqlite3.Connection, job: JobEntry) -> None:
def delete_from_staging(conn: sqlite3.Connection, job: JobEntry) -> None:
def get_next_staging(conn: sqlite3.Connection) -> JobEntry | None:

def write_job_to_discarded(conn: sqlite3.Connection, job: JobEntry) -> None:

def write_job_to_jobs(conn: sqlite3.Connection, job: JobEntry) -> None:"""








