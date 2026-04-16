"""Search and discovery tools.

MCP tools for finding tee times, getting course info,
and suggesting alternatives when a slot isn't available.
"""

from __future__ import annotations

import json
from typing import Optional

from ..db.connection import get_connection
from ..db.models import AlternativeSuggestion, GolfCourse, SearchResult, TeeTime
from ..db import queries


def search_tee_times(
    date: str,
    num_players: int,
    course_name: Optional[str] = None,
    time_range_start: str = "06:00",
    time_range_end: str = "18:00",
) -> dict:
    """Search for available tee times.

    Args:
        date: Desired date in YYYY-MM-DD format.
        num_players: Number of players (1-4).
        course_name: Optional partial or full course name for filtering.
        time_range_start: Earliest acceptable time (HH:MM). Defaults to 06:00.
        time_range_end: Latest acceptable time (HH:MM). Defaults to 18:00.

    Returns:
        Dictionary with available tee times and total count.
    """
    # Build query with optional course filter
    course_filter = ""
    params: dict = {
        "date": date,
        "num_players": num_players,
        "time_start": time_range_start,
        "time_end": time_range_end,
    }

    if course_name:
        course_filter = queries.SEARCH_TEE_TIMES_COURSE_FILTER
        params["course_name"] = f"%{course_name}%"

    query = queries.SEARCH_TEE_TIMES.format(course_filter=course_filter)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    tee_times = [TeeTime(**dict(row)) for row in rows]
    result = SearchResult(available_tee_times=tee_times, total_results=len(tee_times))
    return result.model_dump()


def get_course_info(
    course_id: Optional[int] = None,
    course_name: Optional[str] = None,
) -> dict:
    """Get details about a golf course.

    Args:
        course_id: Course ID for exact lookup.
        course_name: Partial or full course name for fuzzy lookup.
            At least one of course_id or course_name must be provided.

    Returns:
        Dictionary with course details or an error message.
    """
    if not course_id and not course_name:
        return {"error": "Please provide either a course_id or course_name."}

    with get_connection() as conn:
        if course_id:
            row = conn.execute(queries.GET_COURSE_BY_ID, {"course_id": course_id}).fetchone()
        else:
            row = conn.execute(
                queries.GET_COURSE_BY_NAME, {"course_name": f"%{course_name}%"}
            ).fetchone()

    if not row:
        return {"error": f"No course found matching your search."}

    course = GolfCourse(**dict(row))
    result = course.model_dump()

    # Parse amenities JSON for readability
    if result.get("amenities"):
        try:
            result["amenities"] = json.loads(result["amenities"])
        except json.JSONDecodeError:
            pass

    return result


def suggest_alternatives(
    date: str,
    time_range_start: str,
    num_players: int,
    course_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: int = 50,
) -> dict:
    """Suggest alternative tee times or nearby courses.

    Called when user's first choice is unavailable. Returns two types
    of suggestions:
    - Nearby courses with availability at the requested time
    - Alternative time slots at the originally requested course

    Args:
        date: Originally requested date (YYYY-MM-DD).
        time_range_start: Originally requested start time (HH:MM).
        num_players: Number of players.
        course_name: Original course name (for alternative time search).
        latitude: User's latitude (for nearby course search).
        longitude: User's longitude (for nearby course search).
        radius_km: Search radius in km (default 50).

    Returns:
        Dictionary with nearby_courses and alternative_times lists.
    """
    nearby: list[TeeTime] = []
    alternatives: list[TeeTime] = []

    # Calculate a 2-hour time window around the requested time
    time_end = time_range_start  # Use same time for nearby search

    with get_connection() as conn:
        # 1. Find nearby courses with availability
        if latitude is not None and longitude is not None:
            rows = conn.execute(
                queries.NEARBY_COURSES,
                {
                    "lat": latitude,
                    "lng": longitude,
                    "num_players": num_players,
                    "date": date,
                    "time_start": time_range_start,
                    "time_end": "23:59",
                },
            ).fetchall()
            nearby = [TeeTime(**dict(row)) for row in rows]
        else:
            # If no coordinates, just find any available courses at this time
            rows = conn.execute(
                queries.SEARCH_TEE_TIMES.format(course_filter=""),
                {
                    "date": date,
                    "num_players": num_players,
                    "time_start": time_range_start,
                    "time_end": "23:59",
                },
            ).fetchall()
            nearby = [TeeTime(**dict(row)) for row in rows]

        # 2. Find alternative times at the same course
        if course_name:
            rows = conn.execute(
                queries.ALTERNATIVE_TIMES,
                {
                    "course_name": f"%{course_name}%",
                    "num_players": num_players,
                    "date": date,
                    "time_start": time_range_start,
                    "time_end": time_end,
                },
            ).fetchall()
            alternatives = [TeeTime(**dict(row)) for row in rows]

    message_parts = []
    if nearby:
        message_parts.append(f"Found {len(nearby)} available slots at other courses.")
    if alternatives:
        message_parts.append(f"Found {len(alternatives)} alternative time slots at the requested course.")
    if not nearby and not alternatives:
        message_parts.append("No alternatives found. Try a different date or expand your search criteria.")

    result = AlternativeSuggestion(
        nearby_courses=nearby,
        alternative_times=alternatives,
        message=" ".join(message_parts),
    )
    return result.model_dump()
