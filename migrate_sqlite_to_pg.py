"""Copies data from the local G Drive SQLite DB into the Postgres DB named by DATABASE_URL."""
import os
import sqlite3

import psycopg2
import psycopg2.extras

SQLITE_PATH = r"G:\My Drive\RAM_DATA\ram_crm_db\ram_crm.db"
DATABASE_URL = os.environ["DATABASE_URL"]

TABLES = {
    "clients": ["client_id", "first", "last", "first_2", "last_2", "client_name", "street", "apt",
                "city", "st", "zip", "cell", "cell_2", "email", "realtor", "comments", "reference",
                "storage", "stager", "bday"],
    "rolodex": ["contact_id", "contact_type", "first", "last", "contact_name", "cell", "email",
                "link", "firm", "branch", "street", "city", "st", "zip", "comments"],
    "jobs": ["job_id", "date", "start", "eod", "job1", "job2", "job3", "job4", "job5",
             "crew1", "crew2", "crew3", "crew4", "crew5", "desc1", "desc2", "desc3", "desc4", "desc5"],
    "users": ["username", "password_hash", "display_name", "role"],
}


def main():
    sconn = sqlite3.connect(SQLITE_PATH)
    sconn.row_factory = sqlite3.Row
    pconn = psycopg2.connect(DATABASE_URL)
    pcur = pconn.cursor()

    for table, cols in TABLES.items():
        rows = sconn.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
        placeholders = ", ".join(["%s"] * len(cols))
        colnames = ", ".join(cols)
        pk = cols[0]
        update_cols = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols[1:])
        for r in rows:
            pcur.execute(
                f"""INSERT INTO {table} ({colnames}) VALUES ({placeholders})
                    ON CONFLICT ({pk}) DO UPDATE SET {update_cols}""",
                tuple(r),
            )
        print(f"{table}: {len(rows)} rows migrated")

    pconn.commit()
    pconn.close()
    sconn.close()


if __name__ == "__main__":
    main()
