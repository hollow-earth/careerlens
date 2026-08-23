import pytest
import src.database as database
import sqlite3 


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    database.init_tables(conn)
    yield conn
    conn.close()