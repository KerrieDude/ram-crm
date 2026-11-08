import os
import pandas as pd
import streamlit as st

from db import get_conn, init_db, DB_PATH
from auth import login_wall

st.set_page_config(page_title="RAM CRM", page_icon="assets/logo.png" if os.path.exists("assets/logo.png") else "📋", layout="wide")

init_db()
user = login_wall()

with st.sidebar:
    if os.path.exists("assets/logo.png"):
        st.image("assets/logo.png", width=80)
    st.markdown("## Run Around Melissa")
    st.caption(f"Signed in as **{user['display_name']}** ({user['role']})")
    if st.button("Sign out"):
        del st.session_state["user"]
        st.rerun()
    st.divider()
    page = st.radio("Go to", ["Clients", "Rolodex", "Jobs", "Settings"])
    st.divider()
    st.caption(f"DB: `{DB_PATH}`")

conn = get_conn()


def table_page(title, table, search_cols):
    st.header(title)
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn.raw)
    q = st.text_input("Search")
    if q:
        mask = False
        for c in search_cols:
            if c in df.columns:
                mask = mask | df[c].astype(str).str.contains(q, case=False, na=False)
        df = df[mask]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} rows")


if page == "Clients":
    table_page("Clients", "clients", ["client_name", "first", "last", "street", "city", "email", "cell"])
elif page == "Rolodex":
    table_page("Rolodex (Realtors / Contacts)", "rolodex", ["contact_name", "firm", "email", "cell", "city"])
elif page == "Jobs":
    table_page("Daily Jobs", "jobs", ["job1", "job2", "crew1", "date"])
elif page == "Settings":
    st.header("Settings")
    st.markdown(
        """
        **Database location**
        The CRM database currently lives on Google Drive at:
        """
    )
    st.code(DB_PATH)
    st.markdown(
        """
        To move it later (e.g. to a managed Postgres DB or a server disk), set the
        `RAM_CRM_DB_PATH` environment variable to the new SQLite path, or swap `db.py`
        for a different connection — nothing else in the app needs to change.
        """
    )
    if user["role"] == "admin":
        st.divider()
        st.subheader("Add a user")
        with st.form("add_user"):
            nu = st.text_input("New username")
            np_ = st.text_input("New password", type="password")
            dn = st.text_input("Display name")
            role = st.selectbox("Role", ["staff", "admin"])
            if st.form_submit_button("Create user"):
                from auth import hash_pw
                conn.execute(
                    "INSERT OR REPLACE INTO users (username, password_hash, display_name, role) VALUES (?,?,?,?)",
                    (nu, hash_pw(np_), dn, role),
                )
                conn.commit()
                st.success(f"User '{nu}' created.")

conn.close()
