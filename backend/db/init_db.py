"""Initialize the SQLite database schema.

Run this module directly to create all tables:
    python -m backend.db.init_db
"""

import sys
from pathlib import Path

# Allow running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from typing import Optional

from backend.mcp_server.db.connection import get_connection
from backend.mcp_server.db.queries import CREATE_TABLES


def init_database(db_path: Optional[Path] = None) -> None:
    """Create all tables and indexes if they don't exist."""
    with get_connection(db_path) as conn:
        conn.executescript(CREATE_TABLES)
        # Migration: add password_hash column if missing (existing DBs)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "password_hash" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        if "home_area" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN home_area TEXT")
        if "travel_mode" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN travel_mode TEXT DEFAULT 'train'")
        if "max_travel_minutes" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN max_travel_minutes INTEGER DEFAULT 60")
    print(f"✅ Database initialized successfully.")


if __name__ == "__main__":
    init_database()
