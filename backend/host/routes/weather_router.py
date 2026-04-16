"""Weather API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.services.weather import get_weather_forecast

router = APIRouter(prefix="/api/weather", tags=["weather"])


class WeatherOut(BaseModel):
    course_name: str | None = None
    course_location: str | None = None
    requested_datetime: str | None = None
    forecast_datetime: str | None = None
    temperature_c: float | None = None
    precipitation_probability: float | None = None
    precipitation_mm: float | None = None
    wind_speed_kmh: float | None = None
    weather_code: int | None = None
    weather_description: str | None = None
    assessment: str | None = None
    message: str | None = None
    error: str | None = None


@router.get("", response_model=WeatherOut)
def weather_lookup(
    course_name: str = Query(..., min_length=1),
    date: str = Query(..., min_length=10, max_length=10),
    time: str = Query(..., min_length=5, max_length=5),
):
    return get_weather_forecast(course_name=course_name, date=date, time=time)
