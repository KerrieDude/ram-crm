"""One-time import of RAM_CRM_2.0.xlsx (clients, RolodexDB, RAM_database) into the SQLite CRM DB."""
import sys
import openpyxl
from db import get_conn, init_db

XLSX_PATH = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\jesov\Downloads\RAM_CRM_2.0.xlsx"


def rows(ws, start=2):
    for row in ws.iter_rows(min_row=start, values_only=True):
        if row and any(v is not None for v in row):
            yield row


def s(v):
    return "" if v is None else str(v)


def main():
    init_db()
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    conn = get_conn()
    n = 0
    for r in rows(wb["clients"]):
        conn.execute(
            """INSERT OR REPLACE INTO clients
            (client_id, first, last, first_2, last_2, client_name, street, apt, city, st, zip,
             cell, cell_2, email, realtor, comments, reference, storage, stager, bday)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s(r[0]), s(r[1]), s(r[2]), s(r[3]), s(r[4]), s(r[5]), s(r[6]), s(r[7]), s(r[8]),
             s(r[9]), s(r[10]), s(r[11]), s(r[12]), s(r[13]), s(r[14]), s(r[15]), s(r[16]),
             s(r[17]), s(r[18]), s(r[19])),
        )
        n += 1
    print(f"clients: {n}")

    n = 0
    for r in rows(wb["RolodexDB"]):
        conn.execute(
            """INSERT OR REPLACE INTO rolodex
            (contact_id, contact_type, first, last, contact_name, cell, email, link, firm, branch,
             street, city, st, zip, comments)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s(r[0]), s(r[1]), s(r[2]), s(r[3]), s(r[4]), s(r[5]), s(r[6]), s(r[7]), s(r[8]),
             s(r[9]), s(r[10]), s(r[11]), s(r[12]), s(r[13]), s(r[14])),
        )
        n += 1
    print(f"rolodex: {n}")

    n = 0
    for i, r in enumerate(rows(wb["save_date"], start=6)):
        date_val = r[2] if len(r) > 2 else None
        client = r[3] if len(r) > 3 else None
        type_ = r[4] if len(r) > 4 else None
        addr = r[5] if len(r) > 5 else None
        if not (client or addr):
            continue
        conn.execute(
            "INSERT OR REPLACE INTO save_dates (save_id, date, client, type, address) VALUES (?,?,?,?,?)",
            (f"sd-{i}", s(date_val), s(client), s(type_), s(addr)),
        )
        n += 1
    print(f"save_dates: {n}")

    rate_rows = {
        "crew_rate": 30, "management": 90, "fuel_surcharge": 6, "mpg": 10,
        "environmental_fee": 5, "vehicle_licensing_fee": 2.5, "liability_insurance": 10,
        "day_rate_penske": 50, "day_rate_uhaul": 85,
        "mile_rate_penske": 0.19, "mile_rate_uhaul": 0.59,
        "tax": 0.0625, "free_miles_uhaul": 75,
        "cuft_per_mover_hour": 60, "base_access_hours": 1,
        "painting_rate_per_sqft": 2.5, "carpentry_hourly_rate": 65,
        "landscaping_hourly_rate": 55,
    }
    for k, v in rate_rows.items():
        conn.execute("INSERT OR REPLACE INTO rates (rate_key, rate_value) VALUES (?,?)", (k, str(v)))
    print(f"rates: {len(rate_rows)}")

    n = 0
    for r in rows(wb["RAM_database"]):
        conn.execute(
            """INSERT OR REPLACE INTO jobs
            (job_id, date, start, eod, job1, job2, job3, job4, job5,
             crew1, crew2, crew3, crew4, crew5, desc1, desc2, desc3, desc4, desc5)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s(r[0]), s(r[1]), s(r[2]), s(r[3]), s(r[4]), s(r[5]), s(r[6]), s(r[7]), s(r[8]),
             s(r[9]), s(r[10]), s(r[11]), s(r[12]), s(r[13]), s(r[14]), s(r[15]), s(r[16]),
             s(r[17]), s(r[18])),
        )
        n += 1
    print(f"jobs: {n}")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
