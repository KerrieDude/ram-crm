import os
import re
import sqlite3

# Local/default: SQLite file on G Drive. Set DATABASE_URL (a postgres:// URL) to switch
# to a cloud-hosted Postgres DB instead -- that's what Streamlit Community Cloud needs,
# since it can't see a local G Drive path. Everything else in the app is unaffected.
DEFAULT_DB_PATH = r"G:\My Drive\RAM_DATA\ram_crm_db\ram_crm.db"
DB_PATH = os.environ.get("RAM_CRM_DB_PATH", DEFAULT_DB_PATH)
DATABASE_URL = os.environ.get("DATABASE_URL")

USING_POSTGRES = bool(DATABASE_URL)


class Conn:
    """Wraps sqlite3 or psycopg2 behind one tiny interface so call sites never branch."""

    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, params=()):
        cur = self.raw.cursor()
        if USING_POSTGRES:
            sql = re.sub(r"\?", "%s", sql)
            sql = sql.replace("INSERT OR REPLACE INTO", "INSERT INTO")
        cur.execute(sql, params)
        return cur

    def commit(self):
        self.raw.commit()

    def close(self):
        self.raw.close()


def get_conn():
    if USING_POSTGRES:
        import psycopg2
        import psycopg2.extras

        raw = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return Conn(raw)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    raw = sqlite3.connect(DB_PATH, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return Conn(raw)


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'staff'
);

CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY,
    first TEXT, last TEXT,
    first_2 TEXT, last_2 TEXT,
    client_name TEXT,
    street TEXT, apt TEXT, city TEXT, st TEXT, zip TEXT,
    cell TEXT, cell_2 TEXT, email TEXT,
    realtor TEXT, comments TEXT, reference TEXT,
    storage TEXT, stager TEXT, bday TEXT
);

CREATE TABLE IF NOT EXISTS rolodex (
    contact_id TEXT PRIMARY KEY,
    contact_type TEXT,
    first TEXT, last TEXT, contact_name TEXT,
    cell TEXT, email TEXT, link TEXT,
    firm TEXT, branch TEXT,
    street TEXT, city TEXT, st TEXT, zip TEXT, comments TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    date TEXT, start TEXT, eod TEXT,
    job1 TEXT, job2 TEXT, job3 TEXT, job4 TEXT, job5 TEXT,
    crew1 TEXT, crew2 TEXT, crew3 TEXT, crew4 TEXT, crew5 TEXT,
    desc1 TEXT, desc2 TEXT, desc3 TEXT, desc4 TEXT, desc5 TEXT
);
"""


def init_db():
    conn = get_conn()
    if USING_POSTGRES:
        cur = conn.raw.cursor()
        for stmt in SCHEMA_SQLITE.replace("TEXT", "TEXT").split(";"):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
    else:
        conn.raw.executescript(SCHEMA_SQLITE)
    conn.commit()
    conn.close()
