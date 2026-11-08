import os
import pandas as pd
import streamlit as st

import calendar
import random
import string
import uuid
from datetime import date, datetime

from db import get_conn, init_db, DB_PATH, USING_POSTGRES
from auth import login_wall, hash_pw, list_users, upsert_user, set_password
from theme import inject_css, topbar
from qr import directions_qr_png_bytes, directions_url
from inventory import FURNITURE, WEIGHT_FACTOR_LBS_PER_CUFT
from packing_calc import lookup as packing_lookup, BEDROOM_OPTIONS, PERSON_OPTIONS, TIERS
from labor_ref import (CREW_HOURS, HOME_SIZES, CREW_SIZES, RENT_A_CRATE, RENT_A_CRATE_UNIT,
                        REDI_BOX, REDI_BOX_UNIT, TRUCKS, RENTAL_BRANDS)
from ikea_assembly import IKEA_ITEMS, BRANDS as IKEA_BRANDS, label as ikea_label
from ocr import image_to_text
from vision import identify_items, api_key_configured
from photo_storage import save_photo, save_text
import base64

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


def gen_id():
    """Matches the original spreadsheet's client/contact ID style: a short random
    7-character mixed-case alphanumeric code (e.g. evKAqT8, eDhCAPh)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choices(alphabet, k=7))


def photo_input(key_prefix, label="Take a photo"):
    """Camera only turns on (and asks for permission) after the user clicks a button --
    it never auto-fires just from the tab being open -- and is phone/tablet only (hidden
    on desktop widths via CSS). The upload button is always available on every device."""
    show_key = f"{key_prefix}_show_camera"
    if show_key not in st.session_state:
        st.session_state[show_key] = False
    if not st.session_state[show_key]:
        if st.button(f"📷 {label}", key=f"{key_prefix}_cam_btn"):
            st.session_state[show_key] = True
            st.rerun()
    photo = None
    if st.session_state[show_key]:
        photo = st.camera_input("Camera", key=f"{key_prefix}_camera", label_visibility="collapsed")
    st.markdown("**📁 Upload a photo**")
    uploaded = st.file_uploader(
        "Choose a photo file", type=["jpg", "jpeg", "png"], key=f"{key_prefix}_upload",
        label_visibility="collapsed",
    )
    return photo or uploaded


PAGES = ["Dashboard", "Clients", "Rolodex", "Date Book", "Daily Run", "Quotes", "Billing",
         "Client Manager", "Labor & Expenses", "Notes & Photos", "Sell With Us", "Settings"]

JOB_TYPES = ["", "Move", "Hunni-Do", "Cleanout", "Spec", "Painting", "Carpentry", "Landscaping", "Other"]
NEW_CLIENT_SENTINEL = "+ New client (unscheduled)..."
st.session_state.setdefault("nav_pills", "Dashboard")
nav_page = st.pills("Navigate", PAGES, key="nav_pills")


def goto(page_name):
    st.session_state["nav_pills"] = page_name
    st.rerun()


def table_page(title, table, search_cols, key=None):
    st.subheader(title)
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    df = pd.DataFrame([dict(r) for r in rows])
    q = st.text_input("Search", key=f"search_{key or table}")
    if q:
        mask = False
        for c in search_cols:
            if c in df.columns:
                mask = mask | df[c].astype(str).str.contains(q, case=False, na=False)
        df = df[mask]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} rows")


if nav_page == "Dashboard":
    today = date.today()

    today_jobs = conn.execute("SELECT * FROM jobs WHERE date = ?", (str(today),)).fetchall()
    today_dates = conn.execute("SELECT * FROM save_dates WHERE date = ?", (str(today),)).fetchall()
    upcoming = conn.execute(
        "SELECT * FROM save_dates WHERE date > ? ORDER BY date LIMIT 10", (str(today),)
    ).fetchall()
    upcoming_count = conn.execute(
        "SELECT COUNT(*) AS c FROM save_dates WHERE date > ?", (str(today),)
    ).fetchone()["c"]

    with st.container(key="dash_layout"):
        dash_left, dash_right = st.columns([1, 1], gap="large")

    with dash_left:
        st.subheader(f"Today — {today.strftime('%A, %B %d, %Y')}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Jobs today", len(today_jobs))
        c2.metric("Bookings today", len(today_dates))
        c3.metric("Bookings ahead", upcoming_count)

        st.markdown("**Today's run**")
        if today_jobs:
            st.dataframe(pd.DataFrame([dict(r) for r in today_jobs]), use_container_width=True, hide_index=True)
        else:
            st.caption("Nothing logged for today yet — add it under Daily Run.")

        st.markdown("**Today's bookings**")
        if today_dates:
            df_today = pd.DataFrame([dict(r) for r in today_dates])[["date", "client", "type", "address"]]
            df_today.columns = ["Date", "Client", "Job Type", "Address"]
            st.dataframe(df_today, use_container_width=True, hide_index=True)
        else:
            st.caption("No save-the-date bookings for today.")

        st.divider()
        st.markdown("**Get directions QR for a job address**")
        all_addrs = sorted({r["address"] for r in (today_dates + upcoming) if r["address"]})
        qr_addr = st.selectbox(
            "Pick a booked address, or type any address below",
            [""] + all_addrs,
            key="dash_qr_pick",
        )
        qr_addr_manual = st.text_input("Or enter any address", key="dash_qr_manual")
        final_addr = qr_addr_manual.strip() or qr_addr
        if final_addr:
            qc1, qc2 = st.columns([1, 2])
            with qc1:
                st.image(directions_qr_png_bytes(final_addr), width=160, caption="Scan for directions")
            with qc2:
                st.caption("Crew scans this on their phone to open turn-by-turn directions.")
                st.markdown(f"[Open in Google Maps]({directions_url(final_addr)})")

        selected = st.session_state.get("selected_day")
        if selected:
            st.divider()
            sel_date = datetime.strptime(selected, "%Y-%m-%d").date()
            st.markdown(f"**{sel_date.strftime('%A, %B %d, %Y')}**")
            sel_jobs = conn.execute("SELECT * FROM jobs WHERE date = ?", (selected,)).fetchall()
            sel_bookings = conn.execute("SELECT * FROM save_dates WHERE date = ?", (selected,)).fetchall()
            if sel_jobs:
                st.markdown("*Jobs on the run:*")
                st.dataframe(pd.DataFrame([dict(r) for r in sel_jobs]), use_container_width=True, hide_index=True)
            if sel_bookings:
                st.markdown("*Bookings:*")
                df_sel = pd.DataFrame([dict(r) for r in sel_bookings])[["date", "client", "type", "address"]]
                df_sel.columns = ["Date", "Client", "Job Type", "Address"]
                st.dataframe(df_sel, use_container_width=True, hide_index=True)
            if not sel_jobs and not sel_bookings:
                st.caption("Nothing on the books for this day.")

            st.markdown("**Jump to:**")
            h1, h2, h3, h4 = st.columns(4)
            with h1:
                if st.button("➕ Log a job", use_container_width=True):
                    goto("Daily Run")
            with h2:
                if st.button("📅 Add a booking", use_container_width=True):
                    goto("Date Book")
            with h3:
                if st.button("💰 Make a quote", use_container_width=True):
                    goto("Quotes")
            with h4:
                if st.button("✖ Clear selection", use_container_width=True):
                    st.session_state.pop("selected_day", None)
                    st.rerun()

    with dash_right:
        st.markdown("### Calendar")

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
                f"<h4 style='text-align:center'>{calendar.month_name[st.session_state['cal_month']]} "
                f"{st.session_state['cal_year']}</h4>",
                unsafe_allow_html=True,
            )

        y, m = st.session_state["cal_year"], st.session_state["cal_month"]
        booked = conn.execute(
            "SELECT date, client, type, address FROM save_dates WHERE date LIKE ?", (f"{y:04d}-{m:02d}-%",)
        ).fetchall()
        run_rows = conn.execute(
            "SELECT * FROM jobs WHERE date LIKE ?", (f"{y:04d}-{m:02d}-%",)
        ).fetchall()
        booked_by_day = {}
        for r in booked:
            d = r["date"][-2:]
            booked_by_day.setdefault(d, []).append(dict(r))
        run_by_day = {}
        for r in run_rows:
            d = r["date"][-2:]
            run_by_day.setdefault(d, []).append(dict(r))

        weeks = calendar.monthcalendar(y, m)
        with st.container(key="cal_grid"):
            header_cols = st.columns(7)
            for col, wd in zip(header_cols, ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
                col.markdown(f"<div style='text-align:center;font-size:0.75rem;color:#888'>{wd}</div>",
                             unsafe_allow_html=True)

            is_today = (y == date.today().year and m == date.today().month)
            for week in weeks:
                cols = st.columns(7)
                for col, day in zip(cols, week):
                    if day == 0:
                        col.markdown("&nbsp;")
                        continue
                    dstr = f"{day:02d}"
                    has_booking = dstr in booked_by_day
                    has_run = dstr in run_by_day
                    marker = ("📦" if has_run else "") + ("📅" if has_booking else "")
                    is_selected = st.session_state.get("selected_day") == f"{y:04d}-{m:02d}-{dstr}"
                    btn_label = f"{'🔸' if is_today and day == date.today().day else ''}{day}\n{marker}"
                    if col.button(btn_label, key=f"cal_btn_{y}_{m}_{dstr}",
                                  type="primary" if is_selected else "secondary",
                                  use_container_width=True):
                        st.session_state["selected_day"] = f"{y:04d}-{m:02d}-{dstr}"
                        st.rerun()

        st.caption("📦 = jobs logged · 📅 = booking. Tap a day for details.")

if nav_page == "Clients":
    st.session_state.setdefault("clients_mode", "Search")
    clients_mode = st.pills("Clients", ["Search", "Add"], key="clients_mode")

    if clients_mode == "Add":
        st.subheader("Add a client")
        with st.form("add_client"):
            c1, c2, c3 = st.columns(3)
            with c1:
                cl_first = st.text_input("First name")
                cl_last = st.text_input("Last name")
                cl_cell = st.text_input("Cell")
            with c2:
                cl_email = st.text_input("Email")
                cl_street = st.text_input("Street")
                cl_city = st.text_input("City")
            with c3:
                cl_st = st.text_input("State", value="NJ")
                cl_zip = st.text_input("Zip")
                cl_realtor = st.text_input("Realtor")
            cl_comments = st.text_area("Comments", height=80)
            check_submit = st.form_submit_button("Check & add client")

        def _insert_client(first, last, cell, email, street, city, st_, zip_, realtor, comments):
            new_id = gen_id()
            client_name = f"{first} {last}".strip()
            conn.execute(
                """INSERT OR REPLACE INTO clients
                (client_id, first, last, client_name, street, city, st, zip, cell, email, realtor, comments)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (new_id, first, last, client_name, street, city, st_, zip_, cell, email, realtor, comments),
            )
            conn.commit()
            return new_id, client_name

        if check_submit:
            full_name = f"{cl_first} {cl_last}".strip().lower()
            dupes = conn.execute(
                """SELECT * FROM clients WHERE
                   LOWER(client_name) LIKE ?
                   OR (LOWER(first) = ? AND LOWER(last) = ? AND ? <> '')
                   OR (cell <> '' AND cell = ?)
                   OR (email <> '' AND LOWER(email) = ?)""",
                (f"%{full_name}%", cl_first.lower(), cl_last.lower(), cl_last, cl_cell, cl_email.lower()),
            ).fetchall()
            if dupes:
                st.session_state["client_dupes"] = [dict(d) for d in dupes]
                st.session_state["client_pending"] = dict(
                    first=cl_first, last=cl_last, cell=cl_cell, email=cl_email, street=cl_street,
                    city=cl_city, st=cl_st, zip=cl_zip, realtor=cl_realtor, comments=cl_comments,
                )
            else:
                new_id, client_name = _insert_client(cl_first, cl_last, cl_cell, cl_email, cl_street,
                                                       cl_city, cl_st, cl_zip, cl_realtor, cl_comments)
                st.success(f"Client '{client_name}' added — id: {new_id}")
                st.rerun()

        if st.session_state.get("client_dupes"):
            st.warning("Found existing client(s) that might be the same person — add anyway, or cancel?")
            for d in st.session_state["client_dupes"]:
                st.write(f"- **{d['client_name']}** — {d['city'] or ''} · {d['cell'] or ''} · id `{d['client_id']}`")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("Add as a new client anyway", use_container_width=True):
                    p = st.session_state["client_pending"]
                    new_id, client_name = _insert_client(p["first"], p["last"], p["cell"], p["email"],
                                                           p["street"], p["city"], p["st"], p["zip"],
                                                           p["realtor"], p["comments"])
                    st.success(f"Client '{client_name}' added — id: {new_id}")
                    st.session_state.pop("client_dupes", None)
                    st.session_state.pop("client_pending", None)
                    st.rerun()
            with dc2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.pop("client_dupes", None)
                    st.session_state.pop("client_pending", None)
                    st.rerun()

    else:
        st.subheader("Search clients")
        q = st.text_input("Search by name, phone, email, or address", key="client_search_q")
        if q:
            like = f"%{q.lower()}%"
            results = conn.execute(
                """SELECT * FROM clients WHERE
                   LOWER(client_name) LIKE ? OR LOWER(first) LIKE ? OR LOWER(last) LIKE ?
                   OR cell LIKE ? OR LOWER(email) LIKE ? OR LOWER(street) LIKE ? OR LOWER(city) LIKE ?""",
                (like, like, like, f"%{q}%", like, like, like),
            ).fetchall()
            st.caption(f"{len(results)} match(es)")
            for r in results:
                r = dict(r)
                label = r["client_name"] or f"{r['first']} {r['last']}".strip() or "(unnamed)"
                with st.expander(f"{label} — {r['city'] or ''} (id {r['client_id']})"):
                    st.write(f"**Address:** {r['street'] or ''}, {r['city'] or ''}, {r['st'] or ''} {r['zip'] or ''}")
                    st.write(f"**Cell:** {r['cell'] or '—'}  ·  **Email:** {r['email'] or '—'}")
                    if r["realtor"]:
                        st.write(f"**Realtor:** {r['realtor']}")
                    if r["comments"]:
                        st.write(f"**Comments:** {r['comments']}")

                    name_key = (r["client_name"] or r["last"] or r["first"] or "").strip().lower()
                    name_like = f"%{name_key}%"
                    found_anything = False

                    if name_key:
                        job_rows = conn.execute(
                            """SELECT * FROM jobs WHERE LOWER(job1) LIKE ? OR LOWER(job2) LIKE ?
                               OR LOWER(job3) LIKE ? OR LOWER(job4) LIKE ? OR LOWER(job5) LIKE ?""",
                            (name_like, name_like, name_like, name_like, name_like),
                        ).fetchall()
                        if job_rows:
                            found_anything = True
                            st.markdown("**Jobs on file:**")
                            st.dataframe(pd.DataFrame([dict(x) for x in job_rows]), use_container_width=True, hide_index=True)

                        quote_rows = conn.execute(
                            "SELECT * FROM quotes WHERE LOWER(client_name) LIKE ?", (name_like,)
                        ).fetchall()
                        if quote_rows:
                            found_anything = True
                            st.markdown("**Quotes / billed:**")
                            st.dataframe(pd.DataFrame([dict(x) for x in quote_rows]), use_container_width=True, hide_index=True)

                        booking_rows = conn.execute(
                            "SELECT * FROM save_dates WHERE LOWER(client) LIKE ?", (name_like,)
                        ).fetchall()
                        if booking_rows:
                            found_anything = True
                            st.markdown("**Save-the-date bookings:**")
                            df_b = pd.DataFrame([dict(x) for x in booking_rows])[["date", "type", "address"]]
                            st.dataframe(df_b, use_container_width=True, hide_index=True)

                        note_rows = conn.execute(
                            "SELECT * FROM client_notes WHERE LOWER(client_ref) LIKE ?", (name_like,)
                        ).fetchall()
                        if note_rows:
                            found_anything = True
                            st.markdown("**Notes & photos:**")
                            for n in note_rows:
                                n = dict(n)
                                st.caption(f"{(n['created_at'] or '')[:10]} by {n['logged_by']}")
                                if n["ocr_text"]:
                                    st.write(n["ocr_text"])
                                if n["manual_note"]:
                                    st.write(n["manual_note"])
                                if n.get("photo_base64"):
                                    st.image(base64.b64decode(n["photo_base64"]), width=200)

                        resale_rows = conn.execute(
                            "SELECT * FROM resale_items WHERE LOWER(client_name) LIKE ?", (name_like,)
                        ).fetchall()
                        if resale_rows:
                            found_anything = True
                            st.markdown("**Items for sale:**")
                            for it in resale_rows:
                                it = dict(it)
                                st.write(f"{it['description']} — ${it['asking_price']} ({it['status']})")
                                if it.get("photo_base64"):
                                    st.image(base64.b64decode(it["photo_base64"]), width=150)

                    if not found_anything:
                        st.caption("No jobs, quotes, bookings, or notes on file yet for this client.")
        else:
            st.caption("Type a name, phone, email, or address above to search.")

    st.divider()
    with st.expander("Full client list"):
        table_page("Clients", "clients", ["client_name", "first", "last", "street", "city", "email", "cell"],
                   key="all_clients")

if nav_page == "Rolodex":
    st.subheader("Add a contact")
    with st.form("add_contact"):
        c1, c2, c3 = st.columns(3)
        with c1:
            rd_type = st.selectbox("Contact type", ["realtor", "scrap", "dealer", "stager", "floor",
                                                      "handiman", "plumber", "resale dealer", "other"])
            rd_first = st.text_input("First name", key="rd_first")
            rd_last = st.text_input("Last name", key="rd_last")
        with c2:
            rd_cell = st.text_input("Cell", key="rd_cell")
            rd_email = st.text_input("Email", key="rd_email")
            rd_firm = st.text_input("Firm")
        with c3:
            rd_city = st.text_input("City", key="rd_city")
            rd_st = st.text_input("State", value="NJ", key="rd_st")
            rd_link = st.text_input("Link")
        rd_comments = st.text_area("Comments", height=80, key="rd_comments")
        if st.form_submit_button("Add contact"):
            new_id = gen_id()
            contact_name = f"{rd_first} {rd_last}".strip()
            conn.execute(
                """INSERT OR REPLACE INTO rolodex
                (contact_id, contact_type, first, last, contact_name, cell, email, link, firm, city, st, comments)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (new_id, rd_type, rd_first, rd_last, contact_name, rd_cell, rd_email, rd_link,
                 rd_firm, rd_city, rd_st, rd_comments),
            )
            conn.commit()
            st.success(f"Contact added — id: {new_id}")
            st.rerun()

    st.divider()
    table_page("Rolodex (Realtors / Contacts)", "rolodex", ["contact_name", "firm", "email", "cell", "city"])

if nav_page == "Date Book":
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

if nav_page == "Daily Run":
    st.subheader("Run Around Daily")

    input_col, ticket_col = st.columns([3, 2], gap="large")

    client_rows = conn.execute("SELECT client_id, client_name FROM clients ORDER BY client_name").fetchall()
    client_names = [r["client_name"] for r in client_rows if r["client_name"]]
    crew_rows = conn.execute(
        "SELECT DISTINCT crew1 AS c FROM jobs WHERE crew1<>'' UNION "
        "SELECT DISTINCT crew2 FROM jobs WHERE crew2<>'' UNION "
        "SELECT DISTINCT crew3 FROM jobs WHERE crew3<>'' UNION "
        "SELECT DISTINCT crew4 FROM jobs WHERE crew4<>'' UNION "
        "SELECT DISTINCT crew5 FROM jobs WHERE crew5<>''"
    ).fetchall()
    crew_initials = sorted({(r["c"] or "").strip() for r in crew_rows if (r["c"] or "").strip()})
    crew_options = ["", *crew_initials, "+ New..."]

    with input_col:
        with st.container(key="daily_run_grid"):
            top1, top2, top3 = st.columns(3)
            with top1:
                d = st.date_input("Date", key="run_date")
            with top2:
                start = st.time_input("Start", key="dr_start")
            with top3:
                eod = st.time_input("EOD", key="dr_eod")

            st.markdown("**Jobs**")
            job_vals, desc_vals = [], []
            for i in range(1, 6):
                jc1, jc2 = st.columns([3, 2])
                with jc1:
                    pick = st.selectbox(
                        f"Job {i} — site/client", ["", *client_names, NEW_CLIENT_SENTINEL],
                        key=f"dr_job{i}_pick",
                        label_visibility="collapsed" if i > 1 else "visible",
                    )
                    if pick == NEW_CLIENT_SENTINEL:
                        pick = st.text_input(
                            f"New client name {i}", key=f"dr_job{i}_new",
                            placeholder="New client — site/address", label_visibility="collapsed",
                        )
                    job_vals.append(pick)
                with jc2:
                    desc_vals.append(st.selectbox(
                        f"Type {i}", JOB_TYPES, key=f"dr_desc{i}",
                        label_visibility="collapsed" if i > 1 else "visible",
                    ))

            st.markdown("**Crew**")
            crew_cols = st.columns(5)
            crew_vals = []
            for i, col in enumerate(crew_cols, start=1):
                with col:
                    pick = st.selectbox(f"Crew {i}", crew_options, key=f"dr_crew{i}_pick")
                    if pick == "+ New...":
                        pick = st.text_input(f"New crew {i}", key=f"dr_crew{i}_new",
                                              placeholder="initials", label_visibility="collapsed")
                    crew_vals.append(pick)

            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                submit_db = st.button("💾 Submit to DB", key="dr_submit_db", use_container_width=True)
            with bc2:
                submit_invoice = st.button("🧾 Create Invoice", key="dr_submit_inv", use_container_width=True)
            with bc3:
                clear_run = st.button("🗑️ Clear", key="dr_clear", use_container_width=True)

        if clear_run:
            for i in range(1, 6):
                st.session_state.pop(f"dr_job{i}_pick", None)
                st.session_state.pop(f"dr_job{i}_new", None)
                st.session_state.pop(f"dr_desc{i}", None)
            for i in range(1, 6):
                st.session_state.pop(f"dr_crew{i}_pick", None)
                st.session_state.pop(f"dr_crew{i}_new", None)
            st.session_state.pop("dr_start", None)
            st.session_state.pop("dr_eod", None)
            st.session_state.pop("last_saved_run", None)
            st.rerun()

        if submit_db or submit_invoice:
            existing_lower = {n.lower() for n in client_names}
            for jv in job_vals:
                name = (jv or "").strip()
                if name and name.lower() not in existing_lower:
                    conn.execute(
                        """INSERT OR REPLACE INTO clients
                        (client_id, first, last, client_name, comments) VALUES (?,?,?,?,?)""",
                        (gen_id(), "", "", name, "Auto-added from Daily Run (unscheduled)"),
                    )
                    conn.commit()
                    existing_lower.add(name.lower())

            job_id = str(uuid.uuid4())[:8]
            conn.execute(
                """INSERT OR REPLACE INTO jobs
                (job_id, date, start, eod, job1, job2, job3, job4, job5,
                 crew1, crew2, crew3, crew4, crew5, desc1, desc2, desc3, desc4, desc5)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (job_id, str(d), str(start), str(eod), *job_vals, *crew_vals, *desc_vals),
            )
            conn.commit()
            crew_str = ", ".join(c for c in crew_vals if c)
            st.session_state["last_saved_run"] = {
                "date": str(d), "start": str(start), "eod": str(eod),
                "jobs": [(j, t) for j, t in zip(job_vals, desc_vals) if j],
                "crew": crew_str,
            }
            if submit_invoice:
                st.session_state["invoice_prefill"] = {
                    "client": job_vals[0] if job_vals and job_vals[0] else "",
                    "address": "",
                    "line_items": [
                        {"activity": "Transport", "logistic": crew_str or "Crew", "amount": 0.0},
                        {"activity": desc_vals[0] if desc_vals and desc_vals[0] else "Labor", "logistic": "Crew", "amount": 0.0},
                    ],
                }
                st.success("Run logged — opening invoice...")
                goto("Billing")
            else:
                st.success("Run logged.")
                st.rerun()

    with ticket_col:
        st.markdown("**Ticket**")
        with st.container(key="ticket_box"):
            st.caption(f"{d} · {start}–{eod}")
            live_jobs = [(j, t) for j, t in zip(job_vals, desc_vals) if j]
            if live_jobs:
                for j, t in live_jobs:
                    st.write(f"**{j}** — {t or '—'}")
            else:
                st.caption("No jobs entered yet.")
            live_crew = ", ".join(c for c in crew_vals if c)
            st.write(f"Crew: {live_crew or '—'}")

        last = st.session_state.get("last_saved_run")
        if last:
            st.caption(f"✅ Last saved to DB · {last['date']} · {last['start']}–{last['eod']}")

    st.divider()
    table_page("Daily Run Log", "jobs", ["job1", "job2", "crew1", "date"])

if nav_page == "Quotes":
    st.subheader("Quotes")
    quote_pick = st.pills("Quote type", ["Move", "Hunni-Do", "Painting", "Carpentry", "Landscaping"],
                          default="Move", key="quote_pick")
    st.divider()

    if quote_pick == "Move":
        st.subheader("Moving Quote — Inventory-Driven Estimate")
        rates = get_rates(conn)
        st.caption(
            "Pick items from the real RAM inventory list to get cubic footage and weight, "
            "which drives the crew-hours estimate below. Rates come from Settings → Rates."
        )

        mq_client = st.text_input("Client name", key="mq_client")

        st.markdown("**1. Inventory**")
        total_cuft = 0.0
        item_counts = {}
        rooms = list(FURNITURE.items())
        with st.container(key="move_inventory_grid"):
            for row_start in range(0, len(rooms), 4):
                row_rooms = rooms[row_start:row_start + 4]
                room_cols = st.columns(4)
                for col, (room, items) in zip(room_cols, row_rooms):
                    with col:
                        st.markdown(f'<div class="mq-room-head">{room.upper()}</div>', unsafe_allow_html=True)
                        hc1, hc2, hc3 = st.columns([3, 1, 1])
                        hc1.markdown('<span class="mq-col-label">ITEM</span>', unsafe_allow_html=True)
                        hc2.markdown('<span class="mq-col-label">QTY</span>', unsafe_allow_html=True)
                        hc3.markdown('<span class="mq-col-label">CU FT</span>', unsafe_allow_html=True)
                        for item, cuft in items.items():
                            ic1, ic2, ic3 = st.columns([3, 1, 1])
                            ic1.markdown(f'<span class="mq-item-name">{item}</span>', unsafe_allow_html=True)
                            with ic2:
                                qty = st.number_input(
                                    item, min_value=0, value=0, step=1,
                                    key=f"mq_item_{room}_{item}", label_visibility="collapsed",
                                )
                            line_total = qty * cuft
                            ic3.markdown(f'<span class="mq-cuft">{line_total:g}</span>' if qty else
                                         f'<span class="mq-cuft mq-cuft-dim">{cuft:g}</span>', unsafe_allow_html=True)
                            if qty:
                                item_counts[f"{room}: {item}"] = qty
                                total_cuft += line_total

        total_weight = total_cuft * WEIGHT_FACTOR_LBS_PER_CUFT
        c1, c2 = st.columns(2)
        c1.metric("Total cubic feet", f"{total_cuft:,.1f}")
        c2.metric("Estimated weight (lbs)", f"{total_weight:,.0f}")

        st.markdown("**2. Stops & mileage**")
        st.caption(
            "Add every stop the truck makes — starting from the truck's pickup/depot, through each "
            "additional stop, to the final return. Miles and drive time from each leg roll up into "
            "the total hours, crew time, and mileage cost below."
        )

        if "mq_stops" not in st.session_state:
            st.session_state.mq_stops = [
                {"label": "Truck depot → Origin", "miles": 0.0, "drive_min": 0, "stairs": 0, "elevator": False},
                {"label": "Return to truck depot", "miles": 0.0, "drive_min": 0, "stairs": 0, "elevator": False},
            ]

        total_miles = 0.0
        total_drive_hrs = 0.0
        remove_idx = None
        with st.container(key="mq_stops_grid"):
            hc1, hc2, hc3, hc4, hc5, hc6, hc7 = st.columns([3, 1, 1, 1, 1, 1, 0.6])
            for hcol, htext in zip((hc1, hc2, hc3, hc4, hc5, hc6, hc7),
                                    ("Leg / Stop", "Miles", "Drive (min)", "Stairs", "Elevator", "Adj (hrs)", "")):
                hcol.markdown(f'<span class="mq-col-label">{htext}</span>', unsafe_allow_html=True)

            for i, stop in enumerate(st.session_state.mq_stops):
                c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 1, 1, 1, 1, 1, 0.6])
                with c1:
                    stop["label"] = st.text_input(
                        "Stop", value=stop["label"], key=f"mq_stop_label_{i}", label_visibility="collapsed",
                    )
                with c2:
                    stop["miles"] = st.number_input(
                        "Miles", min_value=0.0, value=float(stop["miles"]), step=0.5,
                        key=f"mq_stop_miles_{i}", label_visibility="collapsed",
                    )
                with c3:
                    stop["drive_min"] = st.number_input(
                        "Drive min", min_value=0, value=int(stop["drive_min"]), step=1,
                        key=f"mq_stop_drive_{i}", label_visibility="collapsed",
                    )
                with c4:
                    stop["stairs"] = st.number_input(
                        "Stairs", min_value=0, value=int(stop["stairs"]), step=1,
                        key=f"mq_stop_stairs_{i}", label_visibility="collapsed",
                    )
                with c5:
                    stop["elevator"] = st.checkbox(
                        "Elevator", value=stop["elevator"], key=f"mq_stop_elev_{i}", label_visibility="collapsed",
                    )
                adj_hrs = stop["stairs"] * 0.25 + (0.5 if stop["elevator"] else 0)
                with c6:
                    st.markdown(f'<span class="mq-cuft">{adj_hrs:.2f}</span>', unsafe_allow_html=True)
                with c7:
                    if len(st.session_state.mq_stops) > 2 and st.button("🗑", key=f"mq_stop_del_{i}"):
                        remove_idx = i
                total_miles += stop["miles"]
                total_drive_hrs += stop["drive_min"] / 60 + adj_hrs

            if st.button("➕ Add stop"):
                st.session_state.mq_stops.insert(
                    len(st.session_state.mq_stops) - 1,
                    {"label": f"Stop {len(st.session_state.mq_stops)}", "miles": 0.0, "drive_min": 0,
                     "stairs": 0, "elevator": False},
                )
                st.rerun()

        if remove_idx is not None:
            st.session_state.mq_stops.pop(remove_idx)
            st.rerun()

        sm1, sm2 = st.columns(2)
        sm1.metric("Total miles (truck depot to depot)", f"{total_miles:,.1f}")
        sm2.metric("Total drive + access time", f"{total_drive_hrs:.2f} hrs")

        st.markdown("**3. Crew & truck**")
        with st.form("move_quote"):
            c1, c2 = st.columns(2)
            with c1:
                crew_size = st.number_input("Crew size", min_value=1, value=3)
            with c2:
                truck = st.selectbox("Truck", ["Penske", "U-Haul"])
                if truck in RENTAL_BRANDS and os.path.exists(RENTAL_BRANDS[truck]):
                    st.image(RENTAL_BRANDS[truck], width=100)
            manual_override = st.number_input(
                "Override estimated hours (0 = auto-calculate from inventory + stops)", min_value=0.0, value=0.0, step=0.5
            )
            submitted = st.form_submit_button("Calculate quote")

        if submitted:
            auto_hours = (
                rates["base_access_hours"]
                + total_drive_hrs
                + (total_cuft / max(crew_size, 1) / rates["cuft_per_mover_hour"] if rates["cuft_per_mover_hour"] else 0)
            )
            hours = manual_override if manual_override > 0 else round(auto_hours, 2)

            crew_cost = rates["crew_rate"] * crew_size * hours
            day_rate = rates["day_rate_penske"] if truck == "Penske" else rates["day_rate_uhaul"]
            mile_rate = rates["mile_rate_penske"] if truck == "Penske" else rates["mile_rate_uhaul"]
            free_miles = rates.get("free_miles_uhaul", 0) if truck == "U-Haul" else 0
            billable_miles = max(0, total_miles - free_miles)
            truck_cost = day_rate + billable_miles * mile_rate
            fees = (rates["fuel_surcharge"] + rates["environmental_fee"]
                    + rates["vehicle_licensing_fee"] + rates["liability_insurance"])
            subtotal = crew_cost + rates["management"] + truck_cost + fees
            total = subtotal * (1 + rates["tax"])

            st.metric("Estimated total", f"${total:,.2f}")
            st.write(f"Estimated hours: {hours:.2f} (auto: {auto_hours:.2f}) · "
                     f"Crew: ${crew_cost:,.2f} · Management: ${rates['management']:,.2f} · "
                     f"Truck ({truck}): ${truck_cost:,.2f} · Fees: ${fees:,.2f} · Tax: {rates['tax']*100:.2f}%")
            st.caption(f"Route: {total_miles:,.1f} mi across {len(st.session_state.mq_stops)} legs, "
                       f"{total_drive_hrs:.2f} hrs drive + access")
            if item_counts:
                st.caption("Inventory: " + "; ".join(f"{k} ×{v}" for k, v in item_counts.items()))

            conn.execute(
                "INSERT OR REPLACE INTO quotes (quote_id, kind, client_name, created_at, details, total) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4())[:8], "move", mq_client, datetime.utcnow().isoformat(),
                 f"{truck}, crew {crew_size}, {hours:.2f}h, {total_miles:.1f}mi, {total_cuft:.0f}cuft", f"{total:.2f}"),
            )
            conn.commit()
            st.success("Quote saved.")

        st.divider()
        st.markdown("**Packing materials recommendation**")
        st.caption("From RAM's real packing calculator (by home size, persons, and packing tier).")
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            pm_bedrooms = st.selectbox("Bedrooms", BEDROOM_OPTIONS, index=2)
        with pc2:
            pm_persons = st.selectbox("Persons (13+ age)", PERSON_OPTIONS, index=1)
        with pc3:
            pm_tier = st.selectbox("Packing tier", TIERS, index=4)
        pm = packing_lookup(pm_bedrooms, pm_persons, pm_tier)
        if pm:
            st.dataframe(
                pd.DataFrame([{
                    "Medium Boxes": pm["medium_boxes"], "Large Boxes": pm["large_boxes"],
                    "X-Boxes": pm["x_boxes"], "Picture Boxes": pm["picture_boxes"],
                    "Kitchen/Book Boxes": pm["kitchen_book_boxes"], "Wardrobe Boxes": pm["wardrobe_boxes"],
                }]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("No match for that combination.")

        st.divider()
        table_page("Saved Move Quotes", "quotes", ["client_name", "kind", "details"], key="move_quotes")


    if quote_pick == "Hunni-Do":
        st.subheader("Hunni-Do / Cleanout Quote — Auto Estimate")
        rates = get_rates(conn)

        st.markdown("**IKEA / furniture assembly builder**")
        st.caption("Pick items to assemble — this fills in the suggested hours and crew size below.")
        brand_filter = st.multiselect("Filter by brand", IKEA_BRANDS)
        items_to_show = [i for i in IKEA_ITEMS if not brand_filter or i["brand"] in brand_filter]
        picked = st.multiselect(
            "Items to assemble",
            options=[ikea_label(i) for i in items_to_show],
            key="hq_ikea_picked",
        )
        picked_items = [i for i in items_to_show if ikea_label(i) in picked]
        suggested_hours = round(sum(i["hours"] for i in picked_items), 2)
        suggested_crew = max((i["crew"] for i in picked_items), default=1)
        if picked_items:
            st.write(f"Suggested: **{suggested_hours} hours**, crew of **{suggested_crew}** "
                     f"(based on {len(picked_items)} item(s) — assumes sequential assembly by one crew).")

        with st.form("hunni_quote"):
            c1, c2 = st.columns(2)
            with c1:
                hq_client = st.text_input("Client name", key="hq_client")
                crew_size = st.number_input("Crew size", min_value=1, value=suggested_crew or 2, key="hq_crew")
                hours = st.number_input(
                    "Estimated hours", min_value=0.5,
                    value=suggested_hours if suggested_hours > 0 else 3.0, step=0.5, key="hq_hours",
                )
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

            assembly_note = f", assembly: {', '.join(picked)}" if picked else ""
            conn.execute(
                "INSERT OR REPLACE INTO quotes (quote_id, kind, client_name, created_at, details, total) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4())[:8], "hunni-do", hq_client, datetime.utcnow().isoformat(),
                 f"crew {crew_size}, {hours}h, disposal ${disposal}, {miles}mi{assembly_note}", f"{total:.2f}"),
            )
            conn.commit()
            st.success("Quote saved.")

        st.divider()
        table_page("Saved Hunni-Do Quotes", "quotes", ["client_name", "kind", "details"], key="hunni_quotes")


    if quote_pick == "Painting":
        st.subheader("Painting Quote — Auto Estimate")
        rates = get_rates(conn)
        with st.form("painting_quote"):
            c1, c2 = st.columns(2)
            with c1:
                pq_client = st.text_input("Client name", key="pq_client")
                sqft = st.number_input("Square footage to paint", min_value=0.0, value=500.0, step=50.0)
                coats = st.number_input("Coats", min_value=1, value=2)
            with c2:
                rooms = st.number_input("Rooms", min_value=1, value=1)
                prep_level = st.selectbox("Prep level", ["Light (clean walls)", "Standard (patch/sand)", "Heavy (repairs)"])
            submitted = st.form_submit_button("Calculate quote")

        if submitted:
            prep_mult = {"Light (clean walls)": 1.0, "Standard (patch/sand)": 1.15, "Heavy (repairs)": 1.35}[prep_level]
            base = sqft * rates["painting_rate_per_sqft"] * (coats / 2) * prep_mult
            setup_fee = rooms * 25
            subtotal = base + setup_fee
            total = subtotal * (1 + rates["tax"])

            st.metric("Estimated total", f"${total:,.2f}")
            st.write(f"Paint/labor: ${base:,.2f} · Room setup: ${setup_fee:,.2f} · Tax: {rates['tax']*100:.2f}%")

            conn.execute(
                "INSERT OR REPLACE INTO quotes (quote_id, kind, client_name, created_at, details, total) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4())[:8], "painting", pq_client, datetime.utcnow().isoformat(),
                 f"{sqft}sqft, {coats} coats, {rooms} rooms, {prep_level}", f"{total:.2f}"),
            )
            conn.commit()
            st.success("Quote saved.")

        st.divider()
        table_page("Saved Painting Quotes", "quotes", ["client_name", "kind", "details"], key="painting_quotes")


    if quote_pick == "Carpentry":
        st.subheader("Carpentry / Handyman Quote — Auto Estimate")
        rates = get_rates(conn)
        with st.form("carpentry_quote"):
            c1, c2 = st.columns(2)
            with c1:
                cq_client = st.text_input("Client name", key="cq_client")
                hours = st.number_input("Estimated hours", min_value=0.5, value=3.0, step=0.5, key="cq_hours")
            with c2:
                materials_cost = st.number_input("Materials cost ($)", min_value=0.0, value=0.0)
                trip_fee = st.number_input("Trip / travel fee ($)", min_value=0.0, value=0.0)
            job_desc = st.text_input("Job description (e.g. shelving, trim, door repair)")
            submitted = st.form_submit_button("Calculate quote")

        if submitted:
            labor = hours * rates["carpentry_hourly_rate"]
            subtotal = labor + materials_cost + trip_fee
            total = subtotal * (1 + rates["tax"])

            st.metric("Estimated total", f"${total:,.2f}")
            st.write(f"Labor: ${labor:,.2f} · Materials: ${materials_cost:,.2f} · "
                     f"Trip fee: ${trip_fee:,.2f} · Tax: {rates['tax']*100:.2f}%")

            conn.execute(
                "INSERT OR REPLACE INTO quotes (quote_id, kind, client_name, created_at, details, total) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4())[:8], "carpentry", cq_client, datetime.utcnow().isoformat(),
                 f"{job_desc}, {hours}h, materials ${materials_cost}", f"{total:.2f}"),
            )
            conn.commit()
            st.success("Quote saved.")

        st.divider()
        table_page("Saved Carpentry Quotes", "quotes", ["client_name", "kind", "details"], key="carpentry_quotes")


    if quote_pick == "Landscaping":
        st.subheader("Landscaping / Yard Quote — Auto Estimate")
        rates = get_rates(conn)
        with st.form("landscaping_quote"):
            c1, c2 = st.columns(2)
            with c1:
                lq_client = st.text_input("Client name", key="lq_client")
                crew_size = st.number_input("Crew size", min_value=1, value=2, key="lq_crew")
                hours = st.number_input("Estimated hours", min_value=0.5, value=2.0, step=0.5, key="lq_hours")
            with c2:
                service = st.selectbox("Service", ["Mow/Trim", "Cleanup/Leaves", "Mulch/Beds", "Planting", "Hauling/Debris"])
                recurring = st.selectbox("Frequency", ["One-time", "Weekly", "Bi-weekly", "Monthly"])
            submitted = st.form_submit_button("Calculate quote")

        if submitted:
            labor = crew_size * hours * rates["landscaping_hourly_rate"]
            discount = 0.9 if recurring != "One-time" else 1.0
            total = labor * discount * (1 + rates["tax"])

            st.metric("Estimated total" + (" (recurring rate)" if recurring != "One-time" else ""), f"${total:,.2f}")
            st.write(f"Labor: ${labor:,.2f} · Service: {service} · Frequency: {recurring} · Tax: {rates['tax']*100:.2f}%")

            conn.execute(
                "INSERT OR REPLACE INTO quotes (quote_id, kind, client_name, created_at, details, total) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4())[:8], "landscaping", lq_client, datetime.utcnow().isoformat(),
                 f"{service}, crew {crew_size}, {hours}h, {recurring}", f"{total:.2f}"),
            )
            conn.commit()
            st.success("Quote saved.")

        st.divider()
        table_page("Saved Landscaping Quotes", "quotes", ["client_name", "kind", "details"], key="landscaping_quotes")


if nav_page == "Billing":
    st.subheader("Invoice")

    prefill = st.session_state.pop("invoice_prefill", {})

    with st.container(key="invoice_sheet"):
        hc1, hc2 = st.columns([2, 1])
        with hc1:
            st.markdown("<div class='inv-title'>invoice</div>", unsafe_allow_html=True)
        with hc2:
            if os.path.exists("assets/ram_mascot.png"):
                st.image("assets/ram_mascot.png", width=70)

        ic1, ic2 = st.columns(2)
        with ic1:
            inv_number = st.text_input("Invoice #", value=prefill.get("invoice_number", gen_id()))
            inv_date = st.date_input("Date", value=date.today())
        with ic2:
            inv_client = st.text_input("Bill to — Client", value=prefill.get("client", ""))
            inv_address = st.text_input("Address", value=prefill.get("address", ""))

        st.markdown(
            "<div class='inv-company'>RUN AROUND MELISSA<br>270 Claremont Ave<br>Montclair, NJ 07042"
            "<br>908-295-4506<br>melissa@runaroundmelissa.com</div>",
            unsafe_allow_html=True,
        )

        st.markdown("**Activity**")
        default_lines = prefill.get("line_items") or [
            {"activity": "Supervision and Administration", "logistic": "Supervisor", "amount": 0.0},
            {"activity": "Packing", "logistic": "Packers", "amount": 0.0},
            {"activity": "Transport", "logistic": "Crew", "amount": 0.0},
            {"activity": "", "logistic": "Truck", "amount": 0.0},
            {"activity": "", "logistic": "Driver", "amount": 0.0},
            {"activity": "Unpacking", "logistic": "Packers", "amount": 0.0},
            {"activity": "Miscellaneous", "logistic": "Materials", "amount": 0.0},
        ]

        lc1, lc2, lc3 = st.columns([3, 2, 2])
        with lc1:
            st.caption("Activity")
        with lc2:
            st.caption("Logistic")
        with lc3:
            st.caption("Amount (US$)")

        line_items = []
        for i, line in enumerate(default_lines):
            r1, r2, r3 = st.columns([3, 2, 2])
            with r1:
                act = st.text_input(f"act_{i}", value=line["activity"], label_visibility="collapsed", key=f"inv_act_{i}")
            with r2:
                log = st.text_input(f"log_{i}", value=line["logistic"], label_visibility="collapsed", key=f"inv_log_{i}")
            with r3:
                amt = st.number_input(f"amt_{i}", value=float(line["amount"]), label_visibility="collapsed",
                                       key=f"inv_amt_{i}", step=10.0)
            line_items.append({"activity": act, "logistic": log, "amount": amt})

        subtotal = sum(l["amount"] for l in line_items)
        tax_rate = st.number_input("Sales tax %", min_value=0.0, value=6.25, step=0.25) / 100
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount

        st.markdown("**Payment methods:** Zelle · Venmo · PayPal · Credit Card (+3.5% surcharge)")

        tc1, tc2 = st.columns(2)
        with tc1:
            st.metric("Subtotal", f"${subtotal:,.2f}")
        with tc2:
            st.metric(f"Total amount due (incl. {tax_rate*100:.2f}% tax)", f"${total:,.2f}")

        st.caption("Thank you for your business! · runaroundmelissa.com · @runaroundmelissamontclair "
                   "· melissa@runaroundmelissa.com · 908-295-4506")
        st.caption("Terms & conditions: payment is due within 15 days.")

    st.divider()
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if st.button("💾 Save to accounting (DB)", use_container_width=True):
            conn.execute(
                """INSERT OR REPLACE INTO invoices
                (invoice_id, invoice_number, invoice_date, client_name, client_address, line_items,
                 subtotal, tax_rate, tax_amount, total, status, created_at, logged_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (gen_id(), inv_number, str(inv_date), inv_client, inv_address,
                 str(line_items), f"{subtotal:.2f}", f"{tax_rate:.4f}", f"{tax_amount:.2f}",
                 f"{total:.2f}", "unpaid", datetime.utcnow().isoformat(), user["username"]),
            )
            conn.commit()
            st.success(f"Invoice {inv_number} saved to accounting records.")
    with bc2:
        body_lines = "%0D%0A".join(
            f"{l['activity']} ({l['logistic']}): ${l['amount']:,.2f}" for l in line_items if l["activity"]
        )
        mailto = (
            f"mailto:?subject=Invoice%20{inv_number}%20from%20Run%20Around%20Melissa"
            f"&body=Hi%20{inv_client.replace(' ', '%20')}%2C%0D%0A%0D%0A{body_lines}"
            f"%0D%0A%0D%0ATotal%20due%3A%20%24{total:,.2f}%0D%0A%0D%0AThank%20you!"
        )
        st.markdown(f"[📧 Email invoice]({mailto})")
        st.caption("Opens your email client with the invoice pre-filled — no automated sending is wired up yet.")
    with bc3:
        st.caption(f"Invoice total: **${total:,.2f}**")

    st.divider()
    with st.expander("All invoices (accounting)"):
        table_page("Invoices", "invoices", ["invoice_number", "client_name", "status"], key="invoices")


if nav_page == "Client Manager":
    st.subheader("Client Manager")
    st.caption("Track who's paid, how, and what's still open across every invoice.")

    PAYMENT_METHODS = ["Zelle", "Venmo", "PayPal", "Credit Card", "Check", "Cash", "Other"]

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        status_filter = st.selectbox("Status", ["All", "Open (unpaid)", "Closed (paid)"])
    with fc2:
        method_filter = st.selectbox("Payment method", ["All"] + PAYMENT_METHODS)
    with fc3:
        date_from = st.date_input("From", value=None, key="cm_from")
    with fc4:
        date_to = st.date_input("To", value=None, key="cm_to")

    name_filter = st.text_input("Client name contains", key="cm_name")

    rows = conn.execute("SELECT * FROM invoices").fetchall()
    rows = [dict(r) for r in rows]

    if status_filter == "Open (unpaid)":
        rows = [r for r in rows if (r["status"] or "unpaid") != "paid"]
    elif status_filter == "Closed (paid)":
        rows = [r for r in rows if r["status"] == "paid"]
    if method_filter != "All":
        rows = [r for r in rows if r["payment_method"] == method_filter]
    if date_from:
        rows = [r for r in rows if r["invoice_date"] and r["invoice_date"] >= str(date_from)]
    if date_to:
        rows = [r for r in rows if r["invoice_date"] and r["invoice_date"] <= str(date_to)]
    if name_filter:
        rows = [r for r in rows if name_filter.lower() in (r["client_name"] or "").lower()]

    total_open = sum(float(r["total"] or 0) for r in rows if (r["status"] or "unpaid") != "paid")
    total_closed = sum(float(r["total"] or 0) for r in rows if r["status"] == "paid")

    m1, m2, m3 = st.columns(3)
    m1.metric("Invoices shown", len(rows))
    m2.metric("Open ($)", f"${total_open:,.2f}")
    m3.metric("Paid ($)", f"${total_closed:,.2f}")

    st.divider()
    if not rows:
        st.caption("No invoices match these filters.")
    for r in sorted(rows, key=lambda x: x["invoice_date"] or "", reverse=True):
        is_paid = r["status"] == "paid"
        icon = "✅" if is_paid else "🟡"
        with st.expander(f"{icon} {r['invoice_number']} — {r['client_name'] or '(no client)'} "
                          f"— ${float(r['total'] or 0):,.2f} — {r['invoice_date']}"):
            st.write(f"**Address:** {r['client_address'] or '—'}")
            st.write(f"**Subtotal:** ${float(r['subtotal'] or 0):,.2f}  ·  "
                     f"**Tax:** ${float(r['tax_amount'] or 0):,.2f}  ·  "
                     f"**Total:** ${float(r['total'] or 0):,.2f}")
            st.write(f"**Status:** {'Paid' if is_paid else 'Open'}"
                     + (f" on {r['paid_date']}" if is_paid and r["paid_date"] else ""))
            st.write(f"**Payment method:** {r['payment_method'] or '—'}")
            st.caption(f"Logged by {r['logged_by']} on {(r['created_at'] or '')[:10]}")

            if not is_paid:
                pc1, pc2, pc3 = st.columns(3)
                with pc1:
                    pm = st.selectbox("Mark paid via", PAYMENT_METHODS, key=f"pm_{r['invoice_id']}")
                with pc2:
                    pd_val = st.date_input("Paid date", value=date.today(), key=f"pd_{r['invoice_id']}")
                with pc3:
                    st.write("")
                    if st.button("✅ Mark as paid", key=f"markpaid_{r['invoice_id']}", use_container_width=True):
                        conn.execute(
                            "UPDATE invoices SET status = ?, payment_method = ?, paid_date = ? WHERE invoice_id = ?",
                            ("paid", pm, str(pd_val), r["invoice_id"]),
                        )
                        conn.commit()
                        st.success("Marked paid.")
                        st.rerun()
            else:
                if st.button("↩ Reopen (mark unpaid)", key=f"reopen_{r['invoice_id']}"):
                    conn.execute(
                        "UPDATE invoices SET status = ?, payment_method = ?, paid_date = ? WHERE invoice_id = ?",
                        ("unpaid", None, None, r["invoice_id"]),
                    )
                    conn.commit()
                    st.rerun()


if nav_page == "Labor & Expenses":
    st.subheader("Labor & Other Expenses")

    st.markdown("**Log an expense**")
    with st.form("add_expense"):
        c1, c2, c3 = st.columns(3)
        with c1:
            ex_date = st.date_input("Date", key="ex_date")
            ex_category = st.selectbox(
                "Category", ["Fuel", "Dump/Disposal", "Equipment Rental", "Supplies/Materials",
                             "Truck/Vehicle", "Parking/Tolls", "Other"]
            )
        with c2:
            ex_job = st.text_input("Job / client reference")
            ex_amount = st.number_input("Amount ($)", min_value=0.0, value=0.0, step=1.0)
        with c3:
            ex_notes = st.text_area("Notes", height=100)
        if st.form_submit_button("Log expense"):
            conn.execute(
                """INSERT OR REPLACE INTO expenses
                (expense_id, date, job_ref, category, amount, notes, logged_by)
                VALUES (?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:8], str(ex_date), ex_job, ex_category,
                 f"{ex_amount:.2f}", ex_notes, user["username"]),
            )
            conn.commit()
            st.success("Expense logged.")
            st.rerun()

    ex_rows = conn.execute("SELECT * FROM expenses ORDER BY date DESC").fetchall()
    df_ex = pd.DataFrame([dict(r) for r in ex_rows])
    if not df_ex.empty:
        df_ex["amount"] = df_ex["amount"].astype(float)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total logged", f"${df_ex['amount'].sum():,.2f}")
        this_month = df_ex[pd.to_datetime(df_ex["date"]).dt.strftime("%Y-%m") == date.today().strftime("%Y-%m")]
        c2.metric("This month", f"${this_month['amount'].sum():,.2f}")
        c3.metric("Entries", len(df_ex))
        st.dataframe(df_ex, use_container_width=True, hide_index=True)
        st.markdown("**By category**")
        st.dataframe(
            df_ex.groupby("category")["amount"].sum().sort_values(ascending=False).reset_index(),
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("No expenses logged yet.")

    st.divider()
    st.markdown("**Crew / hours reference by home size**")
    st.caption("From RAM's own settings sheet — how many hours a given crew size typically needs.")
    ref_c1, ref_c2 = st.columns(2)
    with ref_c1:
        ref_home = st.selectbox("Home size", HOME_SIZES, key="ref_home")
    with ref_c2:
        ref_crew = st.selectbox("Crew size", CREW_SIZES, key="ref_crew")
    hrs = next((h for hs, sqft, c, h in CREW_HOURS if hs == ref_home and c == ref_crew), None)
    if hrs:
        st.metric(f"Typical hours — {ref_home}, crew of {ref_crew}", hrs)
    else:
        st.caption("No reference data for that combination.")
    st.dataframe(
        pd.DataFrame(CREW_HOURS, columns=["Home Size", "Sq Ft", "Crew", "Hours"]),
        use_container_width=True, hide_index=True,
    )

    st.divider()
    st.markdown("**Portable storage pricing reference**")
    pc1, pc2 = st.columns(2)
    with pc1:
        st.markdown(f"*Rent-A-Crate* — {RENT_A_CRATE_UNIT}")
        st.dataframe(
            pd.DataFrame(RENT_A_CRATE, columns=["Home Size", "Boxes", "Dollies"]),
            use_container_width=True, hide_index=True,
        )
    with pc2:
        st.markdown(f"*Redi-Box* — {REDI_BOX_UNIT}")
        st.dataframe(
            pd.DataFrame(REDI_BOX, columns=["Home Size", "Pricing", "Boxes"]),
            use_container_width=True, hide_index=True,
        )

    st.divider()
    st.markdown("**Truck size & fuel-cost estimator**")
    tc1, tc2 = st.columns(2)
    with tc1:
        truck_pick = st.selectbox("Truck", [t["name"] for t in TRUCKS])
        trip_miles = st.number_input("Trip miles (round trip)", min_value=0.0, value=20.0, key="fuel_miles")
    with tc2:
        gas_price = st.number_input("Current gas price ($/gal)", min_value=0.0, value=3.50, step=0.05)
    truck_info = next(t for t in TRUCKS if t["name"] == truck_pick)
    gallons_needed = trip_miles / truck_info["mpg"]
    fuel_cost = gallons_needed * gas_price
    st.write(f"**{truck_info['name']}** — best for *{truck_info['home_size']}*, "
             f"{truck_info['mpg']} mpg, {truck_info['tank_gal']} gal tank "
             f"(~{truck_info['range_mi']} mi range)")
    st.metric("Estimated fuel cost for this trip", f"${fuel_cost:,.2f}", f"{gallons_needed:.1f} gal")

    st.markdown("**Preferred rental partners**")
    logo_cols = st.columns(len(RENTAL_BRANDS))
    for col, (brand, logo_path) in zip(logo_cols, RENTAL_BRANDS.items()):
        with col:
            if os.path.exists(logo_path):
                st.image(logo_path, width=140, caption=brand)

if nav_page == "Notes & Photos":
    st.subheader("Notes & Photos")
    st.caption(
        "Take a photo of a handwritten or typed note and pull the text out automatically, "
        "or snap a photo of a room/item for a furniture ID assist on junk-removal and move quotes."
    )

    note_mode = st.radio("What are you photographing?", ["Handwritten/typed note", "Room or furniture item"],
                          horizontal=True)
    note_client = st.text_input("Client / job reference", key="note_client")
    photo = photo_input("note", "Take a photo")

    if photo is not None:
        img_bytes = photo.getvalue()
        st.image(img_bytes, width=300)

        if note_mode == "Handwritten/typed note":
            if st.button("Extract text from photo"):
                try:
                    with st.spinner("Reading photo..."):
                        text = image_to_text(img_bytes)
                    st.session_state["note_ocr_text"] = text
                except RuntimeError as e:
                    st.error(str(e))

            ocr_text = st.text_area(
                "Extracted text (edit if needed before saving)",
                value=st.session_state.get("note_ocr_text", ""), height=150,
            )
            if st.button("Save note"):
                conn.execute(
                    """INSERT OR REPLACE INTO client_notes
                    (note_id, client_ref, created_at, logged_by, ocr_text, manual_note, photo_base64)
                    VALUES (?,?,?,?,?,?,?)""",
                    (str(uuid.uuid4())[:8], note_client, datetime.utcnow().isoformat(),
                     user["username"], ocr_text, "", base64.b64encode(img_bytes).decode()),
                )
                conn.commit()
                photo_path = save_photo(img_bytes, prefix=f"note_{note_client or 'client'}")
                text_path = save_text(ocr_text, prefix=f"note_{note_client or 'client'}")
                if photo_path:
                    st.success(f"Note saved. Also mirrored to {photo_path} / {text_path}")
                else:
                    st.success("Note saved. (Local photo/text mirror only works when running locally with G Drive mounted.)")
                st.session_state.pop("note_ocr_text", None)
                st.rerun()

        else:
            if not api_key_configured():
                st.info(
                    "Furniture ID isn't active yet — add a GOOGLE_VISION_API_KEY in your "
                    "deployment secrets to turn this on. Until then, tag items by hand below."
                )
            elif st.button("Identify items in photo"):
                with st.spinner("Identifying..."):
                    found, err = identify_items(img_bytes)
                if err:
                    st.warning(err)
                else:
                    st.session_state["note_vision_labels"] = found

            labels = st.session_state.get("note_vision_labels", [])
            if labels:
                st.write("Detected: " + ", ".join(f"{l['description']} ({l['score']:.0%})" for l in labels))

            manual_tags = st.text_input("Items (comma-separated — edit/add to what was detected)",
                                         value=", ".join(l["description"] for l in labels))
            if st.button("Save photo note"):
                conn.execute(
                    """INSERT OR REPLACE INTO client_notes
                    (note_id, client_ref, created_at, logged_by, ocr_text, manual_note, photo_base64)
                    VALUES (?,?,?,?,?,?,?)""",
                    (str(uuid.uuid4())[:8], note_client, datetime.utcnow().isoformat(),
                     user["username"], "", manual_tags, base64.b64encode(img_bytes).decode()),
                )
                conn.commit()
                save_photo(img_bytes, prefix=f"item_{note_client or 'client'}")
                save_text(manual_tags, prefix=f"item_{note_client or 'client'}")
                st.success("Saved.")
                st.session_state.pop("note_vision_labels", None)
                st.rerun()

    st.divider()
    table_page("Saved Notes", "client_notes", ["client_ref", "ocr_text", "manual_note"], key="client_notes")

if nav_page == "Sell With Us":
    st.subheader("Sell With Us — Client Item Intake")
    st.caption("Take a picture of something a client wants to sell (RAM Insiders / resale).")

    st.markdown("**Photo of the item**")
    rs_photo = photo_input("resale", "Take a photo of the item")
    if rs_photo is not None:
        st.image(rs_photo.getvalue(), width=250)

    with st.form("resale_item"):
        c1, c2 = st.columns(2)
        with c1:
            rs_client = st.text_input("Client name")
            rs_desc = st.text_area("Description", height=80)
        with c2:
            rs_price = st.number_input("Asking price ($)", min_value=0.0, value=0.0, step=5.0)
            rs_status = st.selectbox("Status", ["New intake", "Listed", "Sold", "Declined"])
        submitted = st.form_submit_button("Save item")

    if submitted:
        photo_b64 = base64.b64encode(rs_photo.getvalue()).decode() if rs_photo else ""
        ai_labels = ""
        if rs_photo and api_key_configured():
            found, err = identify_items(rs_photo.getvalue())
            if not err:
                ai_labels = ", ".join(l["description"] for l in found)
        conn.execute(
            """INSERT OR REPLACE INTO resale_items
            (item_id, client_name, description, asking_price, status, photo_base64, ai_labels, created_at, logged_by)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4())[:8], rs_client, rs_desc, f"{rs_price:.2f}", rs_status,
             photo_b64, ai_labels, datetime.utcnow().isoformat(), user["username"]),
        )
        conn.commit()
        if rs_photo:
            save_photo(rs_photo.getvalue(), prefix=f"sell_{rs_client or 'client'}")
            save_text(f"{rs_desc}\nAI tags: {ai_labels}", prefix=f"sell_{rs_client or 'client'}")
        st.success("Item saved." + (f" AI-detected: {ai_labels}" if ai_labels else ""))
        st.rerun()

    st.divider()
    st.markdown("**Items on file**")
    items = conn.execute(
        "SELECT * FROM resale_items ORDER BY created_at DESC"
    ).fetchall()
    for it in items:
        it = dict(it)
        with st.expander(f"{it['client_name'] or 'Unknown'} — {it['description'][:40]} — ${it['asking_price']} ({it['status']})"):
            if it["photo_base64"]:
                st.image(base64.b64decode(it["photo_base64"]), width=250)
            st.write(it["description"])
            if it["ai_labels"]:
                st.caption(f"AI tags: {it['ai_labels']}")
            st.caption(f"Logged by {it['logged_by']} on {it['created_at'][:10]}")

if nav_page == "Settings":
    sections = ["Account", "Users", "Rates", "Email (SMTP)", "System"] if user["role"] == "admin" else ["Account"]
    st.session_state.setdefault("settings_section", "Account")
    section = st.pills("Settings", sections, key="settings_section")

    if section == "Account":
        st.subheader("My account")
        with st.form("change_my_password"):
            st.caption(f"Signed in as `{user['username']}`")
            pc1, pc2 = st.columns(2)
            with pc1:
                new_pw = st.text_input("New password", type="password")
            with pc2:
                new_pw2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Change my password"):
                if not new_pw:
                    st.error("Password can't be empty.")
                elif new_pw != new_pw2:
                    st.error("Passwords don't match.")
                else:
                    set_password(conn, user["username"], hash_pw(new_pw))
                    st.success("Password changed.")

    if section == "Users":
        st.subheader("Manage users")
        users = list_users(conn)
        usernames = [u["username"] for u in users]
        st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

        uc1, uc2 = st.columns(2)
        with uc1:
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
        with uc2:
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

    if section == "Rates":
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

    if section == "Email (SMTP)":
        st.subheader("Email (SMTP) configuration")
        st.caption(
            "Sending invoices automatically needs a real SMTP account (Gmail, SendGrid, your host's mail "
            "server, etc.). Save the settings here now — actually wiring up automated sending is a separate "
            "step we haven't built yet; the Billing tab's email button currently opens your own email client "
            "with the invoice pre-filled instead."
        )
        existing = {r["setting_key"]: r["setting_value"] for r in conn.execute("SELECT * FROM app_settings").fetchall()}
        with st.form("smtp_settings"):
            sc1, sc2 = st.columns(2)
            with sc1:
                smtp_host = st.text_input("SMTP host", value=existing.get("smtp_host", ""))
                smtp_port = st.text_input("SMTP port", value=existing.get("smtp_port", "587"))
                smtp_username = st.text_input("SMTP username", value=existing.get("smtp_username", ""))
            with sc2:
                smtp_password = st.text_input(
                    "SMTP password",
                    type="password",
                    placeholder="•••••••• (leave blank to keep current)" if existing.get("smtp_password") else "",
                )
                smtp_from_email = st.text_input("From email", value=existing.get("smtp_from_email", ""))
                smtp_from_name = st.text_input("From name", value=existing.get("smtp_from_name", "Run Around Melissa"))
            if st.form_submit_button("Save email settings"):
                to_save = {
                    "smtp_host": smtp_host, "smtp_port": smtp_port, "smtp_username": smtp_username,
                    "smtp_from_email": smtp_from_email, "smtp_from_name": smtp_from_name,
                }
                if smtp_password:
                    to_save["smtp_password"] = smtp_password
                for k, v in to_save.items():
                    conn.execute("INSERT OR REPLACE INTO app_settings (setting_key, setting_value) VALUES (?,?)", (k, v))
                conn.commit()
                st.success("Email settings saved.")
                st.rerun()

    if section == "System":
        st.subheader("System")
        st.markdown("**Database location**")
        st.code("Postgres (cloud)" if USING_POSTGRES else DB_PATH)

conn.close()
