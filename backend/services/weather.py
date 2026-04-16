"""Weather lookup helpers powered by the Open-Meteo API."""

from __future__ import annotations

from datetime import datetime

import httpx

from backend.mcp_server.db.connection import get_connection

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Moderate showers",
    82: "Violent showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}

BAD_WEATHER_CODES = {65, 67, 73, 75, 77, 82, 85, 86, 95, 96, 99}
CAUTION_WEATHER_CODES = {3, 45, 48, 53, 55, 61, 63, 66, 71, 80, 81}


def _resolve_course(course_name: str):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM golf_courses
            WHERE lower(name) LIKE lower(:course_name)
            ORDER BY CASE WHEN lower(name) = lower(:exact_name) THEN 0 ELSE 1 END, name ASC
            LIMIT 1
            """,
            {"course_name": f"%{course_name}%", "exact_name": course_name},
        ).fetchone()
    return row


def _assessment_for_golf(*, weather_code: int, precipitation_probability: float, precipitation: float, wind_speed: float, temperature: float) -> tuple[str, str]:
    if (
        weather_code in BAD_WEATHER_CODES
        or precipitation_probability >= 60
        or precipitation >= 2.0
        or wind_speed >= 35
    ):
        return "bad", "Conditions look poor for golf"

    if (
        weather_code in CAUTION_WEATHER_CODES
        or precipitation_probability >= 30
        or precipitation > 0
        or wind_speed >= 20
        or temperature < 5
        or temperature > 32
    ):
        return "mixed", "Conditions are playable but not ideal"

    return "good", "Conditions look good for golf"


def meets_default_play_preferences(weather: dict) -> bool:
    """Return True when weather meets the default user-safe play preferences."""
    if not weather or weather.get("error"):
        return False

    precipitation = float(weather.get("precipitation_mm", 0.0) or 0.0)
    wind_speed = float(weather.get("wind_speed_kmh", 0.0) or 0.0)
    weather_code = int(weather.get("weather_code", -1)) if weather.get("weather_code") is not None else -1

    rainy_codes = {51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
    return precipitation <= 0 and wind_speed <= 20 and weather_code not in rainy_codes


def get_weather_forecast(course_name: str, date: str, time: str) -> dict:
    """Return the forecast for a course/date/time and assess golf conditions."""
    requested_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    course = _resolve_course(course_name)
    if not course:
        return {"error": f"No course found matching '{course_name}'."}

    if course["latitude"] is None or course["longitude"] is None:
        return {"error": f"Weather is unavailable because {course['name']} has no coordinates."}

    response = httpx.get(
        OPEN_METEO_URL,
        params={
            "latitude": course["latitude"],
            "longitude": course["longitude"],
            "hourly": "temperature_2m,precipitation_probability,precipitation,wind_speed_10m,weather_code",
            "timezone": "Asia/Tokyo",
            "start_date": date,
            "end_date": date,
        },
        timeout=10.0,
    )
    response.raise_for_status()
    payload = response.json().get("hourly", {})

    timestamps = payload.get("time", [])
    if not timestamps:
        return {"error": f"Forecast is unavailable for {date}."}

    hourly_datetimes = [datetime.fromisoformat(ts) for ts in timestamps]
    index = min(range(len(hourly_datetimes)), key=lambda i: abs(hourly_datetimes[i] - requested_dt))

    forecast_dt = hourly_datetimes[index]
    temperature = payload["temperature_2m"][index]
    precipitation_probability = payload["precipitation_probability"][index]
    precipitation = payload["precipitation"][index]
    wind_speed = payload["wind_speed_10m"][index]
    weather_code = payload["weather_code"][index]
    weather_description = WEATHER_CODES.get(weather_code, "Unknown conditions")
    assessment, summary_prefix = _assessment_for_golf(
        weather_code=weather_code,
        precipitation_probability=precipitation_probability,
        precipitation=precipitation,
        wind_speed=wind_speed,
        temperature=temperature,
    )

    message = (
        f"{summary_prefix}: {weather_description.lower()}, {temperature:.0f}C, "
        f"{precipitation_probability:.0f}% rain chance, {wind_speed:.0f} km/h wind."
    )

    return {
        "course_name": course["name"],
        "course_location": course["location"],
        "requested_datetime": requested_dt.isoformat(timespec="minutes"),
        "forecast_datetime": forecast_dt.isoformat(timespec="minutes"),
        "temperature_c": temperature,
        "precipitation_probability": precipitation_probability,
        "precipitation_mm": precipitation,
        "wind_speed_kmh": wind_speed,
        "weather_code": weather_code,
        "weather_description": weather_description,
        "assessment": assessment,
        "message": message,
    }
