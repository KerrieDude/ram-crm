import os
import pandas as pd
import streamlit as st

import calendar
import uuid
from datetime import date, datetime

from db import get_conn, init_db, DB_PATH, USING_POSTGRES
from auth import login_wall, hash_pw, list_users, upsert_user, set_password
from theme import inject_css, topbar

st.set_page_config(
    page_title="RAM CRM",
    page_icon="assets/ram_mascot.png" if os.path.exists("assets/ram_mascot.png") else "📋",
    layout="wide",
)

inject_css()
init_db()
user = login_wall()
topbar(user)

top_l, top_r = st.columns([5, 1])
with top_r:
    if st.button("Sign out", use_container_width=True):
        del st.session_state["user"]
        st.rerun()

conn = get_conn()

def get_rates(conn):
    rows = conn.execute("SELECT rate_key, rate_value FROM rates").fetchall()
    return {r["rate_key"]: float(r["rate_value"]) for r in rows}


(tab_dashboard, tab_calendar, tab_clients, tab_rolodex, tab_dates, tab_jobs, tab_move_quote,
 tab_hunni_quote, tab_settings) = st.tabs(
    ["Dashboard", "Calendar", "Clients", "Rolodex", "Date Book", "Daily Run",
     "Move Quote", "Hunni-Do Quote", "Settings"]
)


def table_page(title, table, search_cols, key=None):
    st.subheader(title)
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn.raw)
    q = st.text_input("Search", key=f"search_{key or table}")
    if q:
        mask = False
        for c in search_cols:
            if c in df.columns:
                mask = mask | df[c].astype(str).str.contains(q, case=False, na=False)
        df = df[mask]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} rows")


with tab_dashboard:
    today = date.today()
    st.subheader(f"Today — {today.strftime('%A, %B %d, %Y')}")

    today_jobs = conn.execute("SELECT * FROM jobs WHERE date = ?", (str(today),)).fetchall()
    today_dates = conn.execute("SELECT * FROM save_dates WHERE date = ?", (str(today),)).fetchall()

    upcoming_count = conn.execute(
        "SELECT COUNT(*) AS c FROM save_dates WHERE date > ?", (str(today),)
    ).fetchone()["c"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Jobs on the run today", len(today_jobs))
    c2.metric("Bookings today", len(today_dates))
    c3.metric("Bookings ahead", upcoming_count)

    st.markdown("**Today's run**")
    if today_jobs:
        st.dataframe(pd.DataFrame([dict(r) for r in today_jobs]), use_container_width=True, hide_index=True)
    else:
        st.caption("Nothing logged for today yet — add it under Daily Run.")

    st.markdown("**Today's bookings — date, client, and job info**")
    if today_dates:
        df_today = pd.DataFrame([dict(r) for r in today_dates])[["date", "client", "type", "address"]]
        df_today.columns = ["Date", "Client", "Job Type", "Address"]
        st.dataframe(df_today, use_container_width=True, hide_index=True)
    else:
        st.caption("No save-the-date bookings for today.")

    st.markdown("**Coming up — date, client, and job info**")
    upcoming = conn.execute(
        "SELECT * FROM save_dates WHERE date > ? ORDER BY date LIMIT 10", (str(today),)
    ).fetchall()
    if upcoming:
        df_up = pd.DataFrame([dict(r) for r in upcoming])[["date", "client", "type", "address"]]
        df_up.columns = ["Date", "Client", "Job Type", "Address"]
        st.dataframe(df_up, use_container_width=True, hide_index=True)
    else:
        st.caption("Nothing booked ahead yet.")

    st.caption("Open the **Calendar** tab above for the full month view.")

with tab_calendar:
    st.subheader("Calendar")

    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = date.today().year
        st.session_state["cal_month"] = date.today().month

    nav_l, nav_mid, nav_r = st.columns([1, 3, 1])
    with nav_l:
        if st.button("← Prev"):
            m = st.session_state["cal_month"] - 1
            y = st.session_state["cal_year"]
            if m == 0:
                m, y = 12, y - 1
            st.session_state["cal_month"], st.session_state["cal_year"] = m, y
            st.rerun()
    with nav_r:
        if st.button("Next →"):
            m = st.session_state["cal_month"] + 1
            y = st.session_state["cal_year"]
            if m == 13:
                m, y = 1, y + 1
            st.session_state["cal_month"], st.session_state["cal_year"] = m, y
            st.rerun()
    with nav_mid:
        st.markdown(
            f"<h3 style='text-align:center'>{calendar.month_name[st.session_state['cal_month']]} "
            f"{st.session_state['cal_year']}</h3>",
            unsafe_allow_html=True,
        )

    y, m = st.session_state["cal_year"], st.session_state["cal_month"]
    booked = conn.execute(
        "SELECT date, client, type FROM save_dates WHERE date LIKE ?", (f"{y:04d}-{m:02d}-%",)
    ).fetchall()
    run_days = conn.execute(
        "SELECT date FROM jobs WHERE date LIKE ?", (f"{y:04d}-{m:02d}-%",)
    ).fetchall()
    booked_by_day = {}
    for r in booked:
        d = r["date"][-2:]
        booked_by_day.setdefault(d, []).append(f"{r['client'] or ''} ({r['type'] or ''})")
    run_day_set = {r["date"][-2:] for r in run_days}

    weeks = calendar.monthcalendar(y, m)
    header_cols = st.columns(7)
    for col, wd in zip(header_cols, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        col.markdown(f"**{wd}**")

    is_today = (y == date.today().year and m == date.today().month)
    for week in weeks:
        cols = st.columns(7)
        for col, day in zip(cols, week):
            if day == 0:
                col.markdown("&nbsp;", unsafe_allow_html=True)
                continue
            dstr = f"{day:02d}"
            label = f"**{day}**" if (is_today and day == date.today().day) else str(day)
            notes = booked_by_day.get(dstr, [])
            marker = " 📦" if dstr in run_day_set else ""
            cell = label + marker
            if notes:
                cell += "<br><span style='color:#e832c0;font-size:0.75rem'>" + "<br>".join(notes) + "</span>"
            col.markdown(cell, unsafe_allow_html=True)

    st.caption("📦 = jobs logged that day. Pink text = save-the-date bookings.")

with tab_clients:
    table_page("Clients", "clients", ["client_name", "first", "last", "street", "city", "email", "cell"])

with tab_rolodex:
    table_page("Rolodex (Realtors / Contacts)", "rolodex", ["contact_name", "firm", "email", "cell", "city"])

with tab_dates:
    st.subheader("Save the Date — Date Book")
    with st.form("add_save_date"):
        c1, c2, c3 = st.columns(3)
        with c1:
            d = st.date_input("Date")
        with c2:
            client = st.text_input("Client")
        with c3:
            type_ = st.text_input("Type (e.g. Spec, Move, Hunni-Do)")
        addr = st.text_input("Address")
        if st.form_submit_button("Save date"):
            conn.execute(
                "INSERT OR REPLACE INTO save_dates (save_id, date, client, type, address) VALUES (?,?,?,?,?)",
                (str(uuid.uuid4())[:8], str(d), client, type_, addr),
            )
            conn.commit()
            st.success("Date saved.")
            st.rerun()
    table_page("Upcoming / Booked Dates", "save_dates", ["client", "type", "address", "date"])

with tab_jobs:
    st.subheader("Log today's run")
    with st.form("add_daily_run"):
        c1, c2, c3 = st.columns(3)
        with c1:
            d = st.date_input("Date", key="run_date")
            start = st.time_input("Start")
        with c2:
            eod = st.time_input("End of day")
            crew1 = st.text_input("Crew 1 initials")
        with c3:
            crew2 = st.text_input("Crew 2 initials")
            crew3 = st.text_input("Crew 3 initials")
        job1 = st.text_input("Job 1 (site / client)")
        desc1 = st.text_input("Job 1 type (move / hunni-do / cleanout / spec)")
        job2 = st.text_input("Job 2 (site / client)", value="")
        desc2 = st.text_input("Job 2 type", value="")
        if st.form_submit_button("Log run"):
            conn.execute(
                """INSERT OR REPLACE INTO jobs
                (job_id, date, start, eod, job1, job2, crew1, crew2, crew3, desc1, desc2)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:8], str(d), str(start), str(eod), job1, job2,
                 crew1, crew2, crew3, desc1, desc2),
            )
            conn.commit()
            st.success("Run logged.")
            st.rerun()
    st.divider()
    table_page("Daily Run Log", "jobs", ["job1", "job2", "crew1", "date"])

with tab_move_quote:
    st.subheader("Moving Quote — Auto Estimate")
    rates = get_rates(conn)
    st.caption("Rates pulled from Settings → Rates (crew/mileage/fees from the original spreadsheet).")
    with st.form("move_quote"):
        c1, c2 = st.columns(2)
        with c1:
            mq_client = st.text_input("Client name")
            crew_size = st.number_input("Crew size", min_value=1, value=3)
            hours = st.number_input("Estimated hours", min_value=0.5, value=4.0, step=0.5)
        with c2:
            truck = st.selectbox("Truck", ["Penske", "U-Haul"])
            miles = st.number_input("Round-trip miles", min_value=0.0, value=10.0)
        submitted = st.form_submit_button("Calculate quote")

    if submitted:
        crew_cost = rates["crew_rate"] * crew_size * hours
        day_rate = rates["day_rate_penske"] if truck == "Penske" else rates["day_rate_uhaul"]
        mile_rate = rates["mile_rate_penske"] if truck == "Penske" else rates["mile_rate_uhaul"]
        free_miles = rates.get("free_miles_uhaul", 0) if truck == "U-Haul" else 0
        billable_miles = max(0, miles - free_miles)
        truck_cost = day_rate + billable_miles * mile_rate
        fees = (rates["fuel_surcharge"] + rates["environmental_fee"]
                + rates["vehicle_licensing_fee"] + rates["liability_insurance"])
        subtotal = crew_cost + rates["management"] + truck_cost + fees
        total = subtotal * (1 + rates["tax"])

        st.metric("Estimated total", f"${total:,.2f}")
        st.write(f"Crew: ${crew_cost:,.2f} · Management: ${rates['management']:,.2f} · "
                 f"Truck ({truck}): ${truck_cost:,.2f} · Fees: ${fees:,.2f} · Tax: {rates['tax']*100:.2f}%")

        conn.execute(
            "INSERT OR REPLACE INTO quotes (quote_id, kind, client_name, created_at, details, total) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4())[:8], "move", mq_client, datetime.utcnow().isoformat(),
             f"{truck}, crew {crew_size}, {hours}h, {miles}mi", f"{total:.2f}"),
        )
        conn.commit()
        st.success("Quote saved.")

    st.divider()
    table_page("Saved Move Quotes", "quotes", ["client_name", "kind", "details"], key="move_quotes")

with tab_hunni_quote:
    st.subheader("Hunni-Do / Cleanout Quote — Auto Estimate")
    rates = get_rates(conn)
    with st.form("hunni_quote"):
        c1, c2 = st.columns(2)
        with c1:
            hq_client = st.text_input("Client name", key="hq_client")
            crew_size = st.number_input("Crew size", min_value=1, value=2, key="hq_crew")
            hours = st.number_input("Estimated hours", min_value=0.5, value=3.0, step=0.5, key="hq_hours")
        with c2:
            disposal = st.number_input("Disposal / dump fee ($)", min_value=0.0, value=50.0)
            miles = st.number_input("Round-trip miles", min_value=0.0, value=10.0, key="hq_miles")
        submitted = st.form_submit_button("Calculate quote")

    if submitted:
        crew_cost = rates["crew_rate"] * crew_size * hours
        mileage_cost = miles * rates["mile_rate_penske"]
        subtotal = crew_cost + disposal + mileage_cost + rates["fuel_surcharge"] + rates["environmental_fee"]
        total = subtotal * (1 + rates["tax"])

        st.metric("Estimated total", f"${total:,.2f}")
        st.write(f"Crew: ${crew_cost:,.2f} · Disposal: ${disposal:,.2f} · "
                 f"Mileage: ${mileage_cost:,.2f} · Tax: {rates['tax']*100:.2f}%")

        conn.execute(
            "INSERT OR REPLACE INTO quotes (quote_id, kind, client_name, created_at, details, total) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4())[:8], "hunni-do", hq_client, datetime.utcnow().isoformat(),
             f"crew {crew_size}, {hours}h, disposal ${disposal}, {miles}mi", f"{total:.2f}"),
        )
        conn.commit()
        st.success("Quote saved.")

    st.divider()
    table_page("Saved Hunni-Do Quotes", "quotes", ["client_name", "kind", "details"], key="hunni_quotes")

with tab_settings:
    st.subheader("My account")
    with st.form("change_my_password"):
        st.caption(f"Signed in as `{user['username']}`")
        new_pw = st.text_input("New password", type="password")
        new_pw2 = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Change my password"):
            if not new_pw:
                st.error("Password can't be empty.")
            elif new_pw != new_pw2:
                st.error("Passwords don't match.")
            else:
                set_password(conn, user["username"], hash_pw(new_pw))
                st.success("Password changed.")

    if user["role"] == "admin":
        st.divider()
        st.subheader("Manage users")

        users = list_users(conn)
        usernames = [u["username"] for u in users]
        st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

        st.markdown("**Edit an existing user**")
        with st.form("edit_user"):
            target = st.selectbox("User", usernames) if usernames else None
            edit_dn = st.text_input("Display name")
            edit_role = st.selectbox("Role", ["staff", "admin"])
            edit_pw = st.text_input("New password (leave blank to keep current)", type="password")
            if st.form_submit_button("Save changes") and target:
                current = next(u for u in users if u["username"] == target)
                pw_hash = hash_pw(edit_pw) if edit_pw else conn.execute(
                    "SELECT password_hash FROM users WHERE username = ?", (target,)
                ).fetchone()["password_hash"]
                upsert_user(conn, target, pw_hash, edit_dn or current["display_name"], edit_role)
                st.success(f"User '{target}' updated.")
                st.rerun()

        st.markdown("**Add a new user**")
        with st.form("add_user"):
            nu = st.text_input("New username")
            np_ = st.text_input("New password", type="password")
            dn = st.text_input("Display name")
            role = st.selectbox("Role", ["staff", "admin"], key="new_user_role")
            if st.form_submit_button("Create user"):
                if not nu or not np_:
                    st.error("Username and password are required.")
                else:
                    upsert_user(conn, nu, hash_pw(np_), dn, role)
                    st.success(f"User '{nu}' created.")
                    st.rerun()

        st.divider()
        st.subheader("Rates (used by the auto-quote calculators)")
        rates_now = get_rates(conn)
        with st.form("edit_rates"):
            new_vals = {}
            cols = st.columns(3)
            for i, (k, v) in enumerate(sorted(rates_now.items())):
                with cols[i % 3]:
                    new_vals[k] = st.number_input(k, value=v, key=f"rate_{k}")
            if st.form_submit_button("Save rates"):
                for k, v in new_vals.items():
                    conn.execute("INSERT OR REPLACE INTO rates (rate_key, rate_value) VALUES (?,?)", (k, str(v)))
                conn.commit()
                st.success("Rates updated.")
                st.rerun()

        st.divider()
        st.markdown("**Database location**")
        st.code("Postgres (cloud)" if USING_POSTGRES else DB_PATH)

conn.close()
