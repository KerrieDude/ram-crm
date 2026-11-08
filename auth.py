import hashlib
import os
import streamlit as st

from db import get_conn


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def ensure_default_admin():
    """Creates an admin user from env vars on first run if no users exist."""
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    if count == 0:
        user = os.environ.get("RAM_CRM_ADMIN_USER", "melissa")
        pw = os.environ.get("RAM_CRM_ADMIN_PASSWORD", "changeme123")
        conn.execute(
            "INSERT INTO users (username, password_hash, display_name, role) VALUES (?,?,?,?)",
            (user, hash_pw(pw), "Melissa", "admin"),
        )
        conn.commit()
    conn.close()


def check_login(username: str, password: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row:
        row = dict(row)
    if row and row["password_hash"] == hash_pw(password):
        return {"username": row["username"], "display_name": row["display_name"], "role": row["role"]}
    return None


def login_wall():
    """Blocks the rest of the app until a valid login is in session_state. Returns the user dict."""
    if "user" in st.session_state:
        return st.session_state["user"]

    ensure_default_admin()

    st.title("RAM CRM — Sign in")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        user = check_login(username, password)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.stop()
