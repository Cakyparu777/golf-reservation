"""MCP Server — Golf Reservation Tools.

Registers all tools with FastMCP and runs via stdio transport.
This process is spawned by the host (FastAPI) as a subprocess.

Run directly for testing:
    python -m backend.mcp_server.server
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .tools.search import search_tee_times, get_course_info, suggest_alternatives, recommend_tee_times
from .tools.reservation import make_reservation, confirm_reservation, cancel_reservation
from .tools.user import list_user_reservations
from .tools.weather import get_weather_forecast

# Route all logging to stderr so stdout stays clean for JSON-RPC
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_server")

# ---------------------------------------------------------------------------
# FastMCP Instance
# ---------------------------------------------------------------------------

mcp = FastMCP(name="golf-reservation")


# ---------------------------------------------------------------------------
# Tool Registration
# ---------------------------------------------------------------------------

@mcp.tool()
def tool_search_tee_times(
    date: str,
    num_players: int,
    course_name: Optional[str] = None,
    time_range_start: str = "06:00",
    time_range_end: str = "18:00",
) -> dict:
    """Search for available tee times at golf courses.

    Find open tee-time slots based on date, time window, number of players,
    and optionally a specific course name (partial match supported).

    Args:
        date: Desired date in YYYY-MM-DD format.
        num_players: Number of players (1-4).
        course_name: Optional partial or full course name to filter by.
        time_range_start: Earliest acceptable tee time (HH:MM, default "06:00").
        time_range_end: Latest acceptable tee time (HH:MM, default "18:00").
    """
    logger.info(f"search_tee_times: date={date}, players={num_players}, course={course_name}")
    return search_tee_times(
        date=date,
        num_players=num_players,
        course_name=course_name,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
    )


@mcp.tool()
def tool_get_course_info(
    course_id: Optional[int] = None,
    course_name: Optional[str] = None,
) -> dict:
    """Get detailed information about a golf course.

    Provide either a course_id for exact lookup or a course_name for
    fuzzy matching. Returns course details including location, par,
    rating, phone, and amenities.

    Args:
        course_id: Exact course ID.
        course_name: Partial or full course name.
    """
    logger.info(f"get_course_info: id={course_id}, name={course_name}")
    return get_course_info(course_id=course_id, course_name=course_name)


@mcp.tool()
def tool_get_weather_forecast(
    course_name: str,
    date: str,
    time: str,
) -> dict:
    """Get forecast weather for a course at a specific date/time.

    Use this before recommending or booking a tee time when the course,
    date, and time are known. The response includes a golf-friendly
    assessment such as good, mixed, or bad conditions.

    Args:
        course_name: Partial or full course name.
        date: Requested date in YYYY-MM-DD format.
        time: Requested time in HH:MM format.
    """
    logger.info(f"get_weather_forecast: course={course_name}, date={date}, time={time}")
    return get_weather_forecast(course_name=course_name, date=date, time=time)


@mcp.tool()
def tool_suggest_alternatives(
    date: str,
    time_range_start: str,
    num_players: int,
    course_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: int = 50,
) -> dict:
    """Suggest alternative tee times or nearby courses when a slot is unavailable.

    Returns two types of suggestions:
    1. Available slots at nearby courses for the same date/time.
    2. Alternative time slots at the originally requested course (±1 day).

    Args:
        date: Originally requested date (YYYY-MM-DD).
        time_range_start: Originally requested start time (HH:MM).
        num_players: Number of players (1-4).
        course_name: Original course name for alternative time search.
        latitude: User's latitude for nearby course search.
        longitude: User's longitude for nearby course search.
        radius_km: Search radius in kilometers (default 50).
    """
    logger.info(f"suggest_alternatives: date={date}, time={time_range_start}, players={num_players}")
    return suggest_alternatives(
        date=date,
        time_range_start=time_range_start,
        num_players=num_players,
        course_name=course_name,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
    )


@mcp.tool()
def tool_recommend_tee_times(
    date: str,
    num_players: int,
    preferred_time: Optional[str] = None,
    course_name: Optional[str] = None,
    user_area: Optional[str] = None,
    travel_mode: str = "train",
    max_travel_minutes: Optional[int] = 60,
    max_results: int = 3,
) -> dict:
    """Recommend the best tee times using weather, value, and availability.

    Use this when a user asks for the best, recommended, nicest-weather,
    or most suitable tee times.
    """
    logger.info(
        "recommend_tee_times: date=%s, players=%s, preferred_time=%s, course=%s",
        date,
        num_players,
        preferred_time,
        course_name,
    )
    return recommend_tee_times(
        date=date,
        num_players=num_players,
        preferred_time=preferred_time,
        course_name=course_name,
        user_area=user_area,
        travel_mode=travel_mode,
        max_travel_minutes=max_travel_minutes,
        max_results=max_results,
    )


@mcp.tool()
def tool_make_reservation(
    tee_time_id: int,
    user_name: str,
    user_email: str,
    num_players: int,
    user_phone: Optional[str] = None,
) -> dict:
    """Create a pending reservation for a tee time.

    The reservation is held for 10 minutes. The user must confirm it
    within that window or the hold will be released automatically.

    Args:
        tee_time_id: The ID of the tee time to book (from search results).
        user_name: Full name for the booking.
        user_email: Email address for confirmation.
        num_players: Number of players (1-4).
        user_phone: Optional phone number.
    """
    logger.info(f"make_reservation: tee_time={tee_time_id}, user={user_email}, players={num_players}")
    return make_reservation(
        tee_time_id=tee_time_id,
        user_name=user_name,
        user_email=user_email,
        num_players=num_players,
        user_phone=user_phone,
    )


@mcp.tool()
def tool_confirm_reservation(reservation_id: int) -> dict:
    """Confirm a pending reservation to finalize the booking.

    Must be called within 10 minutes of making the reservation.
    Returns a confirmation number on success.

    Args:
        reservation_id: The ID of the pending reservation to confirm.
    """
    logger.info(f"confirm_reservation: id={reservation_id}")
    return confirm_reservation(reservation_id=reservation_id)


@mcp.tool()
def tool_cancel_reservation(
    reservation_id: int,
    reason: Optional[str] = None,
) -> dict:
    """Cancel an existing reservation (pending or confirmed).

    The tee time slot will be released back to the pool.

    Args:
        reservation_id: The ID of the reservation to cancel.
        reason: Optional reason for cancellation.
    """
    logger.info(f"cancel_reservation: id={reservation_id}, reason={reason}")
    return cancel_reservation(reservation_id=reservation_id, reason=reason)


@mcp.tool()
def tool_list_user_reservations(
    user_email: str,
    status_filter: Optional[str] = None,
) -> dict:
    """List all reservations for a user by email.

    Args:
        user_email: The user's email address.
        status_filter: Optional filter: PENDING, CONFIRMED, CANCELLED, EXPIRED, or ALL (default ALL).
    """
    logger.info(f"list_user_reservations: email={user_email}, filter={status_filter}")
    return list_user_reservations(user_email=user_email, status_filter=status_filter)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    """Run the MCP server via stdio transport."""
    logger.info("Starting Golf Reservation MCP server (stdio)...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
