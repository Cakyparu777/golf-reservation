"""Tests for MCP tools — search, reservation, and user tools."""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.seed_data import seed_database
from backend.mcp_server.tools.search import search_tee_times, get_course_info, suggest_alternatives
from backend.mcp_server.tools.search import recommend_tee_times
from backend.mcp_server.tools.reservation import make_reservation, confirm_reservation, cancel_reservation
from backend.mcp_server.tools.user import list_user_reservations
from backend.mcp_server.tools.weather import get_weather_forecast


@pytest.fixture(autouse=True)
def seeded_db(tmp_path):
    """Create and seed a temporary database for every test."""
    path = tmp_path / "test.db"
    os.environ.pop("SUPABASE_PROJECT_REF", None)
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_PUBLISHABLE_KEY", None)
    os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
    os.environ.pop("NEXT_PUBLIC_SUPABASE_URL", None)
    os.environ.pop("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", None)
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
            date=_future_date(), num_players=1, course_name="Wakasu"
        )
        assert result["total_results"] > 0
        for tt in result["available_tee_times"]:
            assert "Wakasu" in tt["course_name"]

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

    def test_search_today_excludes_past_slots(self, monkeypatch):
        fixed_now = datetime(2026, 4, 16, 10, 30, 0)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        monkeypatch.setattr("backend.mcp_server.tools.search.datetime", FixedDateTime)

        from backend.mcp_server.db.connection import get_connection

        today = fixed_now.strftime("%Y-%m-%d")
        with get_connection() as conn:
            course_id = conn.execute("SELECT id FROM golf_courses ORDER BY id LIMIT 1").fetchone()[0]
            conn.execute(
                "DELETE FROM tee_times WHERE date(tee_datetime) BETWEEN date(?, '-1 day') AND date(?, '+1 day')",
                (today, today),
            )
            conn.execute(
                """
                INSERT INTO tee_times (course_id, tee_datetime, max_players, available_slots, price_per_player)
                VALUES (?, ?, 4, 4, ?)
                """,
                (course_id, f"{today}T09:00:00", 100.0),
            )
            conn.execute(
                """
                INSERT INTO tee_times (course_id, tee_datetime, max_players, available_slots, price_per_player)
                VALUES (?, ?, 4, 4, ?)
                """,
                (course_id, f"{today}T10:30:00", 110.0),
            )
            conn.execute(
                """
                INSERT INTO tee_times (course_id, tee_datetime, max_players, available_slots, price_per_player)
                VALUES (?, ?, 4, 4, ?)
                """,
                (course_id, f"{today}T11:00:00", 120.0),
            )
            conn.commit()

        result = search_tee_times(
            date=today,
            num_players=1,
            time_range_start="06:00",
            time_range_end="18:00",
        )

        tee_datetimes = [tt["tee_datetime"] for tt in result["available_tee_times"]]
        assert tee_datetimes == [f"{today}T11:00:00"]


class TestGetCourseInfoTool:
    """Tests for the get_course_info tool."""

    def test_get_by_name(self):
        result = get_course_info(course_name="Tokyo Kokusai")
        assert "error" not in result
        assert "Tokyo Kokusai" in result["name"]

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
            course_name="Wakasu",
        )
        assert result["message"]  # Should have a message

    def test_suggest_alternatives_today_excludes_past_slots(self, monkeypatch):
        fixed_now = datetime(2026, 4, 16, 10, 30, 0)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        monkeypatch.setattr("backend.mcp_server.tools.search.datetime", FixedDateTime)

        from backend.mcp_server.db.connection import get_connection

        today = fixed_now.strftime("%Y-%m-%d")
        with get_connection() as conn:
            courses = conn.execute(
                "SELECT id, name FROM golf_courses ORDER BY id LIMIT 2"
            ).fetchall()
            primary_course_id, primary_course_name = courses[0]["id"], courses[0]["name"]
            nearby_course_id = courses[1]["id"]

            conn.execute(
                "DELETE FROM tee_times WHERE date(tee_datetime) BETWEEN date(?, '-1 day') AND date(?, '+1 day')",
                (today, today),
            )
            conn.execute(
                """
                INSERT INTO tee_times (course_id, tee_datetime, max_players, available_slots, price_per_player)
                VALUES (?, ?, 4, 4, ?)
                """,
                (primary_course_id, f"{today}T09:00:00", 100.0),
            )
            conn.execute(
                """
                INSERT INTO tee_times (course_id, tee_datetime, max_players, available_slots, price_per_player)
                VALUES (?, ?, 4, 4, ?)
                """,
                (nearby_course_id, f"{today}T10:30:00", 110.0),
            )
            conn.execute(
                """
                INSERT INTO tee_times (course_id, tee_datetime, max_players, available_slots, price_per_player)
                VALUES (?, ?, 4, 4, ?)
                """,
                (primary_course_id, f"{today}T11:00:00", 120.0),
            )
            conn.execute(
                """
                INSERT INTO tee_times (course_id, tee_datetime, max_players, available_slots, price_per_player)
                VALUES (?, ?, 4, 4, ?)
                """,
                (nearby_course_id, f"{today}T11:15:00", 130.0),
            )
            conn.commit()

        result = suggest_alternatives(
            date=today,
            time_range_start="06:00",
            num_players=1,
            course_name=primary_course_name,
        )

        nearby_datetimes = [tt["tee_datetime"] for tt in result["nearby_courses"]]
        alternative_datetimes = [tt["tee_datetime"] for tt in result["alternative_times"]]

        assert nearby_datetimes == [f"{today}T11:00:00", f"{today}T11:15:00"]
        assert alternative_datetimes == [f"{today}T11:00:00"]


class TestWeatherTool:
    """Tests for the weather forecast tool."""

    def test_weather_forecast_good_conditions(self, monkeypatch):
        class MockResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "hourly": {
                        "time": ["2026-04-16T11:00", "2026-04-16T12:00"],
                        "temperature_2m": [18.0, 20.0],
                        "precipitation_probability": [10, 15],
                        "precipitation": [0.0, 0.0],
                        "wind_speed_10m": [9.0, 11.0],
                        "weather_code": [1, 2],
                    }
                }

        monkeypatch.setattr("backend.services.weather.httpx.get", lambda *args, **kwargs: MockResponse())

        result = get_weather_forecast(
            course_name="Tama Hills",
            date="2026-04-16",
            time="12:00",
        )

        assert result["course_name"] == "Tama Hills Golf Course"
        assert result["assessment"] == "good"
        assert "good for golf" in result["message"].lower()

    def test_weather_forecast_bad_conditions(self, monkeypatch):
        class MockResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "hourly": {
                        "time": ["2026-04-16T12:00"],
                        "temperature_2m": [14.0],
                        "precipitation_probability": [90],
                        "precipitation": [4.0],
                        "wind_speed_10m": [42.0],
                        "weather_code": [65],
                    }
                }

        monkeypatch.setattr("backend.services.weather.httpx.get", lambda *args, **kwargs: MockResponse())

        result = get_weather_forecast(
            course_name="Wakasu",
            date="2026-04-16",
            time="12:00",
        )

        assert result["course_name"] == "Wakasu Golf Links"
        assert result["assessment"] == "bad"
        assert "poor for golf" in result["message"].lower()


class TestRecommendationTool:
    """Tests for tee time recommendations."""

    def test_recommend_tee_times_prefers_better_weather(self, monkeypatch):
        def fake_weather(course_name: str, date: str, time: str):
            if "Wakasu" in course_name:
                return {
                    "assessment": "good",
                    "weather_code": 1,
                    "precipitation_mm": 0.0,
                    "wind_speed_kmh": 10.0,
                    "message": "Conditions look good for golf: clear sky, 21C, 5% rain chance, 10 km/h wind.",
                }
            return {
                "assessment": "bad",
                "weather_code": 65,
                "precipitation_mm": 4.0,
                "wind_speed_kmh": 35.0,
                "message": "Conditions look poor for golf: heavy rain, 14C, 85% rain chance, 35 km/h wind.",
            }

        monkeypatch.setattr("backend.mcp_server.tools.search.get_weather_forecast", fake_weather)

        result = recommend_tee_times(
            date=_future_date(),
            num_players=1,
            max_results=3,
        )

        assert result["recommended_tee_times"]
        top_pick = result["recommended_tee_times"][0]
        assert top_pick["tee_time"]["course_name"] == "Wakasu Golf Links"
        assert top_pick["weather_assessment"] == "good"

    def test_recommend_tee_times_filters_default_bad_weather(self, monkeypatch):
        def fake_weather(course_name: str, date: str, time: str):
            if "Wakasu" in course_name:
                return {
                    "assessment": "good",
                    "weather_code": 1,
                    "precipitation_mm": 0.0,
                    "wind_speed_kmh": 12.0,
                    "message": "Conditions look good for golf.",
                }
            return {
                "assessment": "mixed",
                "weather_code": 61,
                "precipitation_mm": 1.2,
                "wind_speed_kmh": 24.0,
                "message": "Light rain and windy.",
            }

        monkeypatch.setattr("backend.mcp_server.tools.search.get_weather_forecast", fake_weather)

        result = recommend_tee_times(date=_future_date(), num_players=1, max_results=5)

        assert result["recommended_tee_times"]
        assert all(item["tee_time"]["course_name"] == "Wakasu Golf Links" for item in result["recommended_tee_times"])


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
