"""Tests for MCP tools — search, reservation, and user tools."""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.seed_data import seed_database
from backend.mcp_server.tools.search import search_tee_times, get_course_info, suggest_alternatives
from backend.mcp_server.tools.reservation import make_reservation, confirm_reservation, cancel_reservation
from backend.mcp_server.tools.user import list_user_reservations


@pytest.fixture(autouse=True)
def seeded_db(tmp_path):
    """Create and seed a temporary database for every test."""
    path = tmp_path / "test.db"
    os.environ["DATABASE_PATH"] = str(path)
    seed_database(path)
    yield path
    os.environ.pop("DATABASE_PATH", None)


# Helpers
def _future_date(days: int = 1) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Search Tools
# ---------------------------------------------------------------------------

class TestSearchTeeTimesTool:
    """Tests for the search_tee_times tool."""

    def test_basic_search(self):
        result = search_tee_times(date=_future_date(), num_players=2)
        assert result["total_results"] > 0
        assert len(result["available_tee_times"]) > 0

    def test_search_by_course_name(self):
        result = search_tee_times(
            date=_future_date(), num_players=1, course_name="Pebble Beach"
        )
        assert result["total_results"] > 0
        for tt in result["available_tee_times"]:
            assert "Pebble" in tt["course_name"]

    def test_search_time_range(self):
        result = search_tee_times(
            date=_future_date(),
            num_players=1,
            time_range_start="08:00",
            time_range_end="10:00",
        )
        assert result["total_results"] > 0
        for tt in result["available_tee_times"]:
            hour = int(tt["tee_datetime"].split("T")[1][:2])
            assert 8 <= hour <= 10

    def test_search_no_results(self):
        result = search_tee_times(
            date="2020-01-01",  # Past date, no data
            num_players=1,
        )
        assert result["total_results"] == 0


class TestGetCourseInfoTool:
    """Tests for the get_course_info tool."""

    def test_get_by_name(self):
        result = get_course_info(course_name="Augusta")
        assert "error" not in result
        assert "Augusta" in result["name"]

    def test_get_by_id(self):
        result = get_course_info(course_id=1)
        assert "error" not in result
        assert result["id"] == 1

    def test_not_found(self):
        result = get_course_info(course_name="NonexistentCourse12345")
        assert "error" in result

    def test_no_params(self):
        result = get_course_info()
        assert "error" in result


class TestSuggestAlternativesTool:
    """Tests for the suggest_alternatives tool."""

    def test_suggests_alternatives(self):
        result = suggest_alternatives(
            date=_future_date(),
            time_range_start="08:00",
            num_players=2,
        )
        # Should find some nearby courses
        total = len(result["nearby_courses"]) + len(result["alternative_times"])
        assert total > 0

    def test_suggests_for_specific_course(self):
        result = suggest_alternatives(
            date=_future_date(),
            time_range_start="08:00",
            num_players=2,
            course_name="Pebble Beach",
        )
        assert result["message"]  # Should have a message


# ---------------------------------------------------------------------------
# Reservation Tools
# ---------------------------------------------------------------------------

class TestReservationFlow:
    """Tests for the full reservation lifecycle: make → confirm → cancel."""

    def _get_tee_time_id(self) -> int:
        """Helper: search and return the first available tee_time_id."""
        result = search_tee_times(date=_future_date(), num_players=2)
        return result["available_tee_times"][0]["id"]

    def test_make_reservation(self):
        tee_time_id = self._get_tee_time_id()
        result = make_reservation(
            tee_time_id=tee_time_id,
            user_name="Test User",
            user_email="test@example.com",
            num_players=2,
        )
        assert "error" not in result
        assert result["reservation"]["status"] == "PENDING"
        assert result["reservation"]["num_players"] == 2

    def test_confirm_reservation(self):
        tee_time_id = self._get_tee_time_id()
        make_result = make_reservation(
            tee_time_id=tee_time_id,
            user_name="Test User",
            user_email="test@example.com",
            num_players=2,
        )
        reservation_id = make_result["reservation"]["id"]

        confirm_result = confirm_reservation(reservation_id=reservation_id)
        assert "error" not in confirm_result
        assert confirm_result["reservation"]["status"] == "CONFIRMED"
        assert confirm_result["reservation"]["confirmation_number"] is not None

    def test_cancel_confirmed_reservation(self):
        tee_time_id = self._get_tee_time_id()
        make_result = make_reservation(
            tee_time_id=tee_time_id,
            user_name="Test User",
            user_email="test@example.com",
            num_players=2,
        )
        reservation_id = make_result["reservation"]["id"]
        confirm_reservation(reservation_id=reservation_id)

        cancel_result = cancel_reservation(reservation_id=reservation_id, reason="Testing")
        assert "error" not in cancel_result
        assert cancel_result["reservation"]["status"] == "CANCELLED"

    def test_cancel_pending_reservation(self):
        tee_time_id = self._get_tee_time_id()
        make_result = make_reservation(
            tee_time_id=tee_time_id,
            user_name="Test User",
            user_email="test@example.com",
            num_players=1,
        )
        reservation_id = make_result["reservation"]["id"]

        cancel_result = cancel_reservation(reservation_id=reservation_id)
        assert "error" not in cancel_result
        assert cancel_result["reservation"]["status"] == "CANCELLED"

    def test_slots_restored_on_cancel(self):
        """Cancelling should restore available slots."""
        tee_time_id = self._get_tee_time_id()

        # Check initial slots
        from backend.mcp_server.db.connection import get_connection
        with get_connection() as conn:
            initial_slots = conn.execute(
                "SELECT available_slots FROM tee_times WHERE id = ?", (tee_time_id,)
            ).fetchone()[0]

        # Make and cancel
        make_result = make_reservation(
            tee_time_id=tee_time_id,
            user_name="Test User",
            user_email="test@example.com",
            num_players=2,
        )
        cancel_reservation(reservation_id=make_result["reservation"]["id"])

        # Check slots restored
        with get_connection() as conn:
            final_slots = conn.execute(
                "SELECT available_slots FROM tee_times WHERE id = ?", (tee_time_id,)
            ).fetchone()[0]

        assert final_slots == initial_slots

    def test_make_reservation_invalid_players(self):
        tee_time_id = self._get_tee_time_id()
        result = make_reservation(
            tee_time_id=tee_time_id,
            user_name="Test User",
            user_email="test@example.com",
            num_players=5,
        )
        assert "error" in result

    def test_double_confirm_fails(self):
        tee_time_id = self._get_tee_time_id()
        make_result = make_reservation(
            tee_time_id=tee_time_id,
            user_name="Test User",
            user_email="test@example.com",
            num_players=1,
        )
        reservation_id = make_result["reservation"]["id"]
        confirm_reservation(reservation_id=reservation_id)

        # Second confirm should fail gracefully
        result = confirm_reservation(reservation_id=reservation_id)
        assert "error" in result

    def test_cancel_already_cancelled_fails(self):
        tee_time_id = self._get_tee_time_id()
        make_result = make_reservation(
            tee_time_id=tee_time_id,
            user_name="Test User",
            user_email="test@example.com",
            num_players=1,
        )
        reservation_id = make_result["reservation"]["id"]
        cancel_reservation(reservation_id=reservation_id)

        # Second cancel should fail gracefully
        result = cancel_reservation(reservation_id=reservation_id)
        assert "error" in result


# ---------------------------------------------------------------------------
# User Tools
# ---------------------------------------------------------------------------

class TestListUserReservationsTool:
    """Tests for the list_user_reservations tool."""

    def test_list_empty(self):
        result = list_user_reservations(user_email="nobody@example.com")
        assert result["total"] == 0

    def test_list_with_reservations(self):
        # Create a reservation first
        search_result = search_tee_times(date=_future_date(), num_players=1)
        tee_time_id = search_result["available_tee_times"][0]["id"]
        make_reservation(
            tee_time_id=tee_time_id,
            user_name="List Test User",
            user_email="list@example.com",
            num_players=1,
        )

        result = list_user_reservations(user_email="list@example.com")
        assert result["total"] > 0

    def test_list_with_status_filter(self):
        # Create and confirm a reservation
        search_result = search_tee_times(date=_future_date(), num_players=1)
        tee_time_id = search_result["available_tee_times"][0]["id"]
        make_result = make_reservation(
            tee_time_id=tee_time_id,
            user_name="Filter Test User",
            user_email="filter@example.com",
            num_players=1,
        )
        confirm_reservation(reservation_id=make_result["reservation"]["id"])

        # Filter for confirmed
        confirmed = list_user_reservations(
            user_email="filter@example.com", status_filter="CONFIRMED"
        )
        assert confirmed["total"] > 0

        # Filter for pending (should be 0 after confirming)
        pending = list_user_reservations(
            user_email="filter@example.com", status_filter="PENDING"
        )
        assert pending["total"] == 0
