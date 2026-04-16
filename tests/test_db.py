"""Tests for the database layer — schema, seed data, and queries."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.init_db import init_database
from backend.db.seed_data import seed_database
from backend.mcp_server.db.connection import get_connection
from backend.mcp_server.db.queries import SEARCH_TEE_TIMES, SEARCH_TEE_TIMES_COURSE_FILTER


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database for testing."""
    path = tmp_path / "test.db"
    # Set the env so get_db_path picks it up
    import os
    os.environ.pop("SUPABASE_PROJECT_REF", None)
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_PUBLISHABLE_KEY", None)
    os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
    os.environ.pop("NEXT_PUBLIC_SUPABASE_URL", None)
    os.environ.pop("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", None)
    os.environ["DATABASE_PATH"] = str(path)
    yield path
    os.environ.pop("DATABASE_PATH", None)


@pytest.fixture
def seeded_db(db_path):
    """Create and seed a temporary database."""
    seed_database(db_path)
    return db_path


class TestSchemaCreation:
    """Test database schema initialization."""

    def test_creates_all_tables(self, db_path):
        """All 5 tables should be created."""
        init_database(db_path)
        with get_connection(db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = [t["name"] for t in tables]

        assert "golf_courses" in table_names
        assert "tee_times" in table_names
        assert "users" in table_names
        assert "reservations" in table_names
        assert "reservation_history" in table_names

    def test_idempotent_init(self, db_path):
        """Running init twice should not fail."""
        init_database(db_path)
        init_database(db_path)  # Should not raise


class TestSeedData:
    """Test seed data population."""

    def test_seeds_courses(self, seeded_db):
        """Should insert 5 golf courses."""
        with get_connection(seeded_db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM golf_courses").fetchone()[0]
        assert count == 5

    def test_seeds_tee_times(self, seeded_db):
        """Should generate tee times for all courses and 30 days."""
        with get_connection(seeded_db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM tee_times").fetchone()[0]
        # 5 courses × 24 slots/day × 30 days = 3600
        assert count == 3600

    def test_seed_idempotent(self, db_path):
        """Running seed twice should not duplicate data."""
        seed_database(db_path)
        seed_database(db_path)  # Should print warning and skip
        with get_connection(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM golf_courses").fetchone()[0]
        assert count == 5

    def test_tee_times_have_valid_prices(self, seeded_db):
        """All tee times should have positive prices."""
        with get_connection(seeded_db) as conn:
            min_price = conn.execute(
                "SELECT MIN(price_per_player) FROM tee_times"
            ).fetchone()[0]
            max_price = conn.execute(
                "SELECT MAX(price_per_player) FROM tee_times"
            ).fetchone()[0]
        assert min_price > 0
        assert max_price > 0

    def test_all_slots_start_at_4(self, seeded_db):
        """All tee times should start with 4 available slots."""
        with get_connection(seeded_db) as conn:
            non_four = conn.execute(
                "SELECT COUNT(*) FROM tee_times WHERE available_slots != 4"
            ).fetchone()[0]
        assert non_four == 0


class TestSearchQueries:
    """Test search query construction and execution."""

    def test_search_returns_results(self, seeded_db):
        """Searching for a future date should return results."""
        from datetime import datetime, timedelta

        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        query = SEARCH_TEE_TIMES.format(course_filter="")
        params = {
            "date": future_date,
            "num_players": 2,
            "time_start": "06:00",
            "time_end": "18:00",
        }

        with get_connection(seeded_db) as conn:
            rows = conn.execute(query, params).fetchall()

        assert len(rows) > 0

    def test_search_with_course_filter(self, seeded_db):
        """Search filtered by course name should return only that course."""
        from datetime import datetime, timedelta

        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        query = SEARCH_TEE_TIMES.format(course_filter=SEARCH_TEE_TIMES_COURSE_FILTER)
        params = {
            "date": future_date,
            "num_players": 1,
            "time_start": "06:00",
            "time_end": "18:00",
            "course_name": "%Wakasu%",
        }

        with get_connection(seeded_db) as conn:
            rows = conn.execute(query, params).fetchall()

        assert len(rows) > 0
        for row in rows:
            assert "Wakasu" in row["course_name"]

    def test_search_too_many_players_reduces_results(self, seeded_db):
        """Requesting slots for more players than available should return fewer results."""
        from datetime import datetime, timedelta

        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        query = SEARCH_TEE_TIMES.format(course_filter="")

        with get_connection(seeded_db) as conn:
            # All slots have 4 available, so requesting 5 should return 0
            rows = conn.execute(query, {
                "date": future_date,
                "num_players": 5,
                "time_start": "06:00",
                "time_end": "18:00",
            }).fetchall()

        assert len(rows) == 0
