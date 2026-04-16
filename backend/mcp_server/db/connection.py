"""SQLite connection helper.

Provides a context manager for database connections with WAL mode
and foreign key enforcement enabled.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

# Default DB path — overridden by DATABASE_PATH env var
DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "golf_reservation.db"


def get_db_path() -> Path:
    """Resolve the database file path from env or default."""
    import os

    path = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH)))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with best-practice settings.

    - WAL journal mode for concurrent reads
    - Foreign keys enforced
    - Row factory = sqlite3.Row for dict-like access
    """
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
