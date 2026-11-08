"""Saves photo files and their OCR'd/tagged text alongside the database, mirroring
db.py's path convention: G Drive by default, overridable by env var, swappable later.

Important: this only works where the filesystem path is actually reachable. It works
when the app runs locally (G Drive mounted). On Streamlit Community Cloud the app
has no access to your local G Drive, so writes there are caught and skipped quietly --
the database copy (base64 in Postgres) stays the source of truth for the deployed app.
"""
import os
from datetime import datetime

PHOTO_DB_PATH = os.environ.get("RAM_CRM_PHOTO_DB_PATH", r"G:\My Drive\RAM_DATA\ram_crm_db\photo_db")
TEXT_PHOTO_DB_PATH = os.environ.get("RAM_CRM_TEXT_PHOTO_DB_PATH", r"G:\My Drive\RAM_DATA\ram_crm_db\text_photo_db")


def _safe_name(prefix: str) -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    return f"{prefix}_{stamp}"


def save_photo(image_bytes: bytes, prefix: str = "photo") -> str | None:
    """Saves a photo to PHOTO_DB_PATH. Returns the saved path, or None if it couldn't write
    (e.g. running on Streamlit Cloud where G Drive isn't reachable)."""
    try:
        os.makedirs(PHOTO_DB_PATH, exist_ok=True)
        path = os.path.join(PHOTO_DB_PATH, _safe_name(prefix) + ".jpg")
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path
    except OSError:
        return None


def save_text(text: str, prefix: str = "note") -> str | None:
    """Saves OCR/tag text to TEXT_PHOTO_DB_PATH. Returns the saved path, or None."""
    try:
        os.makedirs(TEXT_PHOTO_DB_PATH, exist_ok=True)
        path = os.path.join(TEXT_PHOTO_DB_PATH, _safe_name(prefix) + ".txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path
    except OSError:
        return None
