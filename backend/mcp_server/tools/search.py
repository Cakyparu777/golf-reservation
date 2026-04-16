"""Search and discovery tools.

MCP tools for finding tee times, getting course info,
and suggesting alternatives when a slot isn't available.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from backend.services.location import estimate_travel_minutes, resolve_area_coordinates
from backend.services.weather import get_weather_forecast
from backend.services.weather import meets_default_play_preferences

from ..db.connection import get_connection
from ..db.models import (
    AlternativeSuggestion,
    GolfCourse,
    RecommendationItem,
    RecommendationResult,
    SearchResult,
    TeeTime,
)
from ..db import queries


def _effective_time_range_start(date: str, time_range_start: str, now: datetime) -> str:
    if date != now.strftime("%Y-%m-%d"):
        return time_range_start

    return max(time_range_start, now.strftime("%H:%M"))


def _exclude_past_tee_times(date: str, tee_times: list[TeeTime], now: datetime) -> list[TeeTime]:
    if date != now.strftime("%Y-%m-%d"):
        return tee_times

    return [
        tee_time
        for tee_time in tee_times
        if datetime.fromisoformat(tee_time.tee_datetime) > now
    ]


def _time_range_for_preference(preferred_time: Optional[str]) -> tuple[str, str]:
    if preferred_time == "morning":
        return ("06:00", "11:30")
    if preferred_time == "afternoon":
        return ("11:30", "16:30")
    if preferred_time == "evening":
        return ("16:00", "18:00")
    return ("06:00", "18:00")


def _recommendation_score(tee_time: TeeTime, weather: Optional[dict]) -> float:
    assessment = str((weather or {}).get("assessment") or "")
    weather_score = {"good": 100.0, "mixed": 70.0, "bad": 35.0}.get(assessment, 55.0)
    value_score = max(0.0, 35.0 - (tee_time.price_per_player / 5.0))
    availability_score = min(float(tee_time.available_slots), 4.0) * 3.0
    return round(weather_score + value_score + availability_score, 2)


def _recommendation_reason(tee_time: TeeTime, weather: Optional[dict]) -> str:
    if not weather or weather.get("error"):
        return "Good availability for your requested date and player count."

    assessment = str(weather.get("assessment") or "")
    if assessment == "good":
        return "Best pick for solid weather and overall value."
    if assessment == "mixed":
        return "Playable option with decent value if you are flexible on conditions."
    return "Available slot, but weather looks challenging compared with other options."


def _append_travel_reason(base_reason: str, travel_minutes: Optional[int]) -> str:
    if travel_minutes is None:
        return base_reason
    return f"{base_reason} Estimated travel time is about {travel_minutes} minutes."


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
    now = datetime.now()
    time_range_start = _effective_time_range_start(date, time_range_start, now)

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

    tee_times = _exclude_past_tee_times(date, [TeeTime(**dict(row)) for row in rows], now)

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
    now = datetime.now()
    nearby: list[TeeTime] = []
    alternatives: list[TeeTime] = []

    # Calculate a 2-hour time window around the requested time
    time_end = time_range_start  # Use same time for nearby search
    time_range_start = _effective_time_range_start(date, time_range_start, now)

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
            nearby = _exclude_past_tee_times(date, [TeeTime(**dict(row)) for row in rows], now)
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
            nearby = _exclude_past_tee_times(date, [TeeTime(**dict(row)) for row in rows], now)

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
            alternatives = _exclude_past_tee_times(date, [TeeTime(**dict(row)) for row in rows], now)

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


def recommend_tee_times(
    date: str,
    num_players: int,
    preferred_time: Optional[str] = None,
    course_name: Optional[str] = None,
    user_area: Optional[str] = None,
    travel_mode: str = "train",
    max_travel_minutes: Optional[int] = 60,
    max_results: int = 3,
) -> dict:
    """Recommend tee times using availability, weather, and value."""
    time_range_start, time_range_end = _time_range_for_preference(preferred_time)
    search_result = search_tee_times(
        date=date,
        num_players=num_players,
        course_name=course_name,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
    )

    candidates = [TeeTime(**row) for row in search_result["available_tee_times"]][:12]
    recommendations: list[RecommendationItem] = []
    fallback_recommendations: list[RecommendationItem] = []
    area_coords = resolve_area_coordinates(user_area)

    for tee_time in candidates:
        weather: Optional[dict] = None
        try:
            weather = get_weather_forecast(
                course_name=tee_time.course_name or course_name or "",
                date=date,
                time=datetime.fromisoformat(tee_time.tee_datetime).strftime("%H:%M"),
            )
        except Exception:
            weather = {"error": "weather service unavailable"}

        travel_minutes = None
        if area_coords:
            travel_minutes = estimate_travel_minutes(
                from_lat=area_coords[0],
                from_lon=area_coords[1],
                to_lat=getattr(tee_time, "course_latitude", None),
                to_lon=getattr(tee_time, "course_longitude", None),
                travel_mode=travel_mode,
            )

        if travel_minutes is None and area_coords:
            with get_connection() as conn:
                course_row = conn.execute(
                    "SELECT latitude, longitude FROM golf_courses WHERE id = :course_id",
                    {"course_id": tee_time.course_id},
                ).fetchone()
            if course_row:
                travel_minutes = estimate_travel_minutes(
                    from_lat=area_coords[0],
                    from_lon=area_coords[1],
                    to_lat=course_row["latitude"],
                    to_lon=course_row["longitude"],
                    travel_mode=travel_mode,
                )

        recommendation = RecommendationItem(
            tee_time=tee_time,
            weather_assessment=None if not weather or weather.get("error") else weather.get("assessment"),
            weather_message=None if not weather or weather.get("error") else weather.get("message"),
            recommendation_reason=_append_travel_reason(_recommendation_reason(tee_time, weather), travel_minutes),
            score=_recommendation_score(tee_time, weather) - (travel_minutes or 0) / 20.0,
        )

        fallback_recommendations.append(recommendation)

        if area_coords and max_travel_minutes is not None and travel_minutes is not None and travel_minutes > max_travel_minutes:
            continue

        if weather and not weather.get("error") and not meets_default_play_preferences(weather):
            continue

        recommendations.append(recommendation)

    recommendations.sort(key=lambda item: (-item.score, item.tee_time.tee_datetime))
    top_recommendations = recommendations[:max_results]
    fallback_recommendations.sort(key=lambda item: (-item.score, item.tee_time.tee_datetime))

    if top_recommendations:
        message = f"Found {len(top_recommendations)} recommended tee times based on weather, value, and availability."
    else:
        if fallback_recommendations:
            message = (
                "No tee times met the default weather and travel preferences. "
                "Try relaxing the weather or travel limits if you want broader suggestions."
            )
        else:
            message = "No recommended tee times found. Try a different date, time preference, or course."

    return RecommendationResult(
        recommended_tee_times=top_recommendations,
        message=message,
    ).model_dump()
