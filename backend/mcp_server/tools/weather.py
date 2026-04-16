"""Weather forecast tool."""

from __future__ import annotations

from backend.services.weather import get_weather_forecast as fetch_weather_forecast


def get_weather_forecast(course_name: str, date: str, time: str) -> dict:
    """Get weather conditions for a course at a requested date/time."""
    return fetch_weather_forecast(course_name=course_name, date=date, time=time)
