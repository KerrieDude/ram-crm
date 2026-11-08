import os
import pandas as pd
import streamlit as st

from db import get_conn, init_db, DB_PATH, USING_POSTGRES
from auth import login_wall, hash_pw, list_users, upsert_user, set_password

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
    st.caption(f"DB: `{'Postgres (cloud)' if USING_POSTGRES else DB_PATH}`")

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
        st.markdown("**Database location**")
        st.code(f"Postgres (cloud)" if USING_POSTGRES else DB_PATH)

conn.close()
