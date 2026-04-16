"""Recommendations API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from backend.mcp_server.tools.search import recommend_tee_times

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class RecommendedTeeTimeOut(BaseModel):
    tee_time: dict
    weather_assessment: Optional[str] = None
    weather_message: Optional[str] = None
    recommendation_reason: str
    score: float


class RecommendationResponse(BaseModel):
    recommended_tee_times: list[RecommendedTeeTimeOut]
    message: str


@router.get("", response_model=RecommendationResponse)
def get_recommendations(
    date: str = Query(..., min_length=10, max_length=10),
    num_players: int = Query(1, ge=1, le=4),
    preferred_time: Optional[str] = Query(None, pattern="^(morning|afternoon|evening)$"),
    course_name: Optional[str] = Query(None),
    user_area: Optional[str] = Query(None),
    travel_mode: Optional[str] = Query("train", pattern="^(train|car|either)$"),
    max_travel_minutes: Optional[int] = Query(60, ge=15, le=240),
    max_results: int = Query(3, ge=1, le=10),
):
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
