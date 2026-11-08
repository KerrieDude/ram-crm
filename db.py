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
            m = re.match(
                r"\s*INSERT OR REPLACE INTO (\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
                sql,
                re.IGNORECASE,
            )
            if m:
                table, cols_raw, _ = m.groups()
                cols = [c.strip() for c in cols_raw.split(",")]
                pk = cols[0]
                placeholders = ", ".join(["%s"] * len(cols))
                update_cols = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols[1:])
                sql = (
                    f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
                    f"ON CONFLICT ({pk}) DO UPDATE SET {update_cols}"
                )
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

CREATE TABLE IF NOT EXISTS save_dates (
    save_id TEXT PRIMARY KEY,
    date TEXT, client TEXT, type TEXT, address TEXT
);

CREATE TABLE IF NOT EXISTS rates (
    rate_key TEXT PRIMARY KEY,
    rate_value TEXT
);

CREATE TABLE IF NOT EXISTS quotes (
    quote_id TEXT PRIMARY KEY,
    kind TEXT,
    client_name TEXT,
    created_at TEXT,
    details TEXT,
    total TEXT
);

CREATE TABLE IF NOT EXISTS expenses (
    expense_id TEXT PRIMARY KEY,
    date TEXT,
    job_ref TEXT,
    category TEXT,
    amount TEXT,
    notes TEXT,
    logged_by TEXT
);

CREATE TABLE IF NOT EXISTS client_notes (
    note_id TEXT PRIMARY KEY,
    client_ref TEXT,
    created_at TEXT,
    logged_by TEXT,
    ocr_text TEXT,
    manual_note TEXT,
    photo_base64 TEXT
);

CREATE TABLE IF NOT EXISTS resale_items (
    item_id TEXT PRIMARY KEY,
    client_name TEXT,
    description TEXT,
    asking_price TEXT,
    status TEXT,
    photo_base64 TEXT,
    ai_labels TEXT,
    created_at TEXT,
    logged_by TEXT
);
"""


MIGRATIONS = [
    "ALTER TABLE client_notes ADD COLUMN photo_base64 TEXT",
]


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

    for stmt in MIGRATIONS:
        try:
            conn.execute(stmt)
            conn.commit()
        except Exception:
            conn.raw.rollback() if USING_POSTGRES else None

    conn.close()
