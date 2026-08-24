from random import randint
from sqlite3.dbapi2 import Connection

from src import database
from src.scrapers.scraper_utilities import CompanyEntry, CompanyTrustStatus, JobEntry, JobStatus, JobSource

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
        idx = randint(1, 999999)
        if idx not in s:
            s.add(idx)
            i += 1
            job = JobEntry(source, f"{idx}", f"https://linkedin.com/{idx}")
            database.write_job_to_ingest(conn, job)
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
    job2 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/555555555")
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
        idx = s.pop()
        database.delete_from_ingest(
            conn,
            JobEntry(JobSource.LINKEDIN, f"{idx}", f"https://linkedin.com/{idx}")
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
        idx = randint(1, 999999)
        if idx not in s:
            s.add(idx)
            i += 1
            job = JobEntry(source, f"{idx}", f"https://linkedin.com/{idx}",
                f"SomeTitle{idx}", f"SomeCompany{idx}", f"SomeLocation{idx}", f"SomeDescription{idx}")
            database.write_job_to_staging(conn, job)
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
    print(len(s), N)
    for _ in range(N):
        idx = s.pop()
        database.delete_from_staging(
            conn,
            JobEntry(JobSource.LINKEDIN, f"{idx}", f"https://linkedin.com/{idx}",
                f"SomeTitle{idx}", f"SomeCompany{idx}", f"SomeLocation{idx}", f"SomeDescription{idx}")
        )
    res = conn.execute("SELECT * FROM staging").fetchall()
    print(len(s), len(res))
    assert len(res) == len(s)


def test_staging_get_next(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789",
        "SomeTitle123456789", "SomeCompany123456789", "SomeLocation123456789", "SomeDescription123456789", JobStatus.READY)
    job2 = JobEntry(JobSource.INDEED, "a7a3467cad7fdedb", "https://indeed.com/viewjob?jk=a7a3467cad7fdedb",
        "SomeTitlea7a3467cad7fdedb", "SomeCompanya7a3467cad7fdedb", "SomeLocationa7a3467cad7fdedb", "SomeDescriptiona7a3467cad7fdedb", JobStatus.READY)
    job3 = JobEntry(JobSource.LINKEDIN, "555555555", "https://linkedin.com/555555555",
        "SomeTitle555555555", "SomeCompany555555555", "SomeLocation555555555", "SomeDescription555555555", JobStatus.READY)
    job4 = JobEntry(JobSource.INDEED, "84ea4a111369c8d7", "https://indeed.com/viewjob?jk=84ea4a111369c8d7",
        "SomeTitle84ea4a111369c8d7", "SomeCompany84ea4a111369c8d7", "SomeLocation84ea4a111369c8d7", "SomeDescription84ea4a111369c8d7", JobStatus.READY)
    job5 = JobEntry(JobSource.LINKEDIN, "555555555", "https://linkedin.com/555555555",
        "SomeTitle555555555", "SomeCompany555555555", "SomeLocation555555555", "SomeDescription555555555", JobStatus.READY)
    database.write_job_to_staging(conn, job1)
    database.write_job_to_staging(conn, job2)
    database.write_job_to_staging(conn, job3)
    database.write_job_to_staging(conn, job4)

    d = database.get_next_staging(conn)
    assert d is not None and d.job_id == job1.job_id
    d = database.get_next_staging(conn)
    assert d is not None and d.job_id == job1.job_id
    d = database.get_next_staging(conn)
    assert d is not None and d.job_id == job1.job_id
    database.delete_from_staging(conn, job1)

    d = database.get_next_staging(conn)
    assert d is not None and d.job_id == job2.job_id
    database.delete_from_staging(conn, job2)

    d = database.get_next_staging(conn)
    assert d is not None and d.job_id == job3.job_id
    database.delete_from_staging(conn, job3)

    database.write_job_to_staging(conn, job5)
    
    d = database.get_next_staging(conn)
    assert d is not None and d.job_id == job4.job_id
    database.delete_from_staging(conn, job4)

    d = database.get_next_staging(conn)
    assert d is not None and d.job_id == job5.job_id
    database.delete_from_staging(conn, job5)

    assert database.get_next_staging(conn) is None
    assert database.get_next_staging(conn) is None


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

def test_jobs_exists_in_pipeline(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription", None, None, 100, "a", "b", "c")
    job2 = JobEntry(JobSource.INDEED, "a7a3467cad7fdedb", "https://indeed.com/viewjob?jk=a7a3467cad7fdedb",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription", None, None, 100, "a", "b", "c")
    database.write_job_to_jobs(conn, job1)
    assert database.job_exists_in_pipeline(conn, job1) is True
    assert database.job_exists_in_pipeline(conn, job2) is False



"""
# ========================================= #
# 
#       Tests with the discarded table
# 
# ========================================= #
"""

def test_discarded_exists_in_pipeline(conn: Connection) -> None:
    job1 = JobEntry(JobSource.LINKEDIN, "123456789", "https://linkedin.com/123456789",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription", None, None, 100, "a", "b", "c", discard_reason="d")
    job2 = JobEntry(JobSource.INDEED, "a7a3467cad7fdedb", "https://indeed.com/viewjob?jk=a7a3467cad7fdedb",
        "SomeTitle", "SomeCompany", "SomeLocation", "SomeDescription", None, None, 100, "a", "b", "c", discard_reason="d")
    database.write_job_to_discarded(conn, job1)
    assert database.job_exists_in_pipeline(conn, job1) is True
    assert database.job_exists_in_pipeline(conn, job2) is False



"""
# ========================================= #
# 
#       Tests with the companies table
# 
# ========================================= #
"""

def test_write_company_to_companies(conn: Connection) -> None:
    a = CompanyEntry("company1", CompanyTrustStatus.TRUSTED)
    b = CompanyEntry("company2", CompanyTrustStatus.BLOCKED)
    c = CompanyEntry("company3", CompanyTrustStatus.UNKNOWN)
    database.write_company_to_companies(conn, a)
    database.write_company_to_companies(conn, a)
    database.write_company_to_companies(conn, a)
    database.write_company_to_companies(conn, b)
    database.write_company_to_companies(conn, c)
    res = conn.execute("SELECT * FROM companies").fetchall()
    assert len(res) == 3

def get_company(conn: Connection) -> None | CompanyEntry:
    a = CompanyEntry("company1", CompanyTrustStatus.TRUSTED)
    b = CompanyEntry("company2", CompanyTrustStatus.BLOCKED)
    c = CompanyEntry("company3", CompanyTrustStatus.UNKNOWN)
    database.write_company_to_companies(conn, a)
    database.write_company_to_companies(conn, b)
    database.write_company_to_companies(conn, c)

    d = database.get_company(conn, "company1")
    e = database.get_company(conn, "company2")
    f = database.get_company(conn, "company3")
    g = database.get_company(conn, "company4")

    assert d is not None and d.normalized_name == "company1"
    assert e is not None and e.normalized_name == "company2"
    assert f is not None and f.normalized_name == "company3"
    assert g is None



"""
# ========================================= #
# 
#       Tests with deduplication
# 
# ========================================= #
"""

# def job_exists_in_pipeline(conn: sqlite3.Connection, job: JobEntry) -> bool:




"""

def write_job_to_discarded(conn: sqlite3.Connection, job: JobEntry) -> None:

def write_job_to_jobs(conn: sqlite3.Connection, job: JobEntry) -> None:"""








