"""Course discovery helpers for nearest-course lookups."""

from __future__ import annotations

from typing import Any, Optional

from backend.mcp_server.db.connection import get_connection
from backend.services.location import estimate_travel_minutes, haversine_km, resolve_area_coordinates
from backend.services.supabase import is_supabase_rest_configured, list_courses as list_supabase_courses


def find_nearest_courses(
    *,
    user_area: str,
    travel_mode: str = "train",
    max_travel_minutes: Optional[int] = 60,
    max_results: int = 3,
) -> dict[str, Any]:
    area_coords = resolve_area_coordinates(user_area)
    if not area_coords:
        return {
            "user_area": user_area,
            "nearest_courses": [],
            "message": "I couldn't resolve that area to a known location.",
        }

    courses = _load_courses()
    ranked_courses: list[dict[str, Any]] = []
    for course in courses:
        latitude = course.get("latitude")
        longitude = course.get("longitude")
        if latitude is None or longitude is None:
            continue

        travel_minutes = estimate_travel_minutes(
            from_lat=area_coords[0],
            from_lon=area_coords[1],
            to_lat=latitude,
            to_lon=longitude,
            travel_mode=travel_mode,
        )
        distance_km = round(haversine_km(area_coords[0], area_coords[1], latitude, longitude), 1)
        if max_travel_minutes is not None and travel_minutes is not None and travel_minutes > max_travel_minutes:
            continue

        ranked_courses.append(
            {
                "id": course.get("id"),
                "name": course.get("name"),
                "location": course.get("location"),
                "rating": course.get("rating"),
                "travel_minutes": travel_minutes,
                "distance_km": distance_km,
            }
        )

    ranked_courses.sort(
        key=lambda item: (
            item.get("travel_minutes") if item.get("travel_minutes") is not None else 10**9,
            item.get("distance_km") if item.get("distance_km") is not None else 10**9,
            -(item.get("rating") or 0.0),
        )
    )

    nearest_courses = ranked_courses[:max_results]
    if nearest_courses:
        return {
            "user_area": user_area,
            "nearest_courses": nearest_courses,
            "message": f"Found {len(nearest_courses)} nearby golf courses for {user_area}.",
        }

    return {
        "user_area": user_area,
        "nearest_courses": [],
        "message": "I couldn't find a nearby course within your current travel limit.",
    }


def _load_courses() -> list[dict[str, Any]]:
    if is_supabase_rest_configured():
        return list_supabase_courses()

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, location, latitude, longitude, rating FROM golf_courses ORDER BY rating DESC"
        ).fetchall()
    return [dict(row) for row in rows]
