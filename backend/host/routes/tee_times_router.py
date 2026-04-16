"""Tee times search API."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from backend.mcp_server.db.connection import get_connection
from backend.mcp_server.db.queries import (
    API_SEARCH_TEE_TIMES,
    API_SEARCH_TEE_TIMES_BY_COURSE,
)

router = APIRouter(prefix="/api/tee-times", tags=["tee-times"])


class TeeTimeOut(BaseModel):
    id: int
    course_id: int
    course_name: str
    course_location: str
    tee_datetime: str
    available_slots: int
    max_players: int
    price_per_player: float


@router.get("", response_model=list[TeeTimeOut])
def search_tee_times(
    course_id: Optional[int] = Query(None),
    num_players: int = Query(1, ge=1, le=4),
    limit: int = Query(20, ge=1, le=100),
):
    with get_connection() as conn:
        if course_id:
            rows = conn.execute(
                API_SEARCH_TEE_TIMES_BY_COURSE,
                {"num_players": num_players, "course_id": course_id, "limit": limit},
            ).fetchall()
        else:
            rows = conn.execute(
                API_SEARCH_TEE_TIMES,
                {"num_players": num_players, "limit": limit},
            ).fetchall()

    return [
        TeeTimeOut(
            id=r["id"],
            course_id=r["course_id"],
            course_name=r["course_name"],
            course_location=r["course_location"],
            tee_datetime=r["tee_datetime"],
            available_slots=r["available_slots"],
            max_players=r["max_players"],
            price_per_player=r["price_per_player"],
        )
        for r in rows
    ]
