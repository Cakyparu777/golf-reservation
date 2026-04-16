"""Courses API routes."""

from __future__ import annotations

import json
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from backend.mcp_server.db.connection import get_connection
from backend.mcp_server.db.queries import LIST_COURSES, GET_COURSE_BY_ID
from backend.services.supabase import (
    get_course as get_supabase_course,
    is_supabase_rest_configured,
    list_courses as list_supabase_courses,
)

router = APIRouter(prefix="/api/courses", tags=["courses"])


class CourseOut(BaseModel):
    id: int
    name: str
    location: str
    holes: int
    par: Optional[int]
    rating: Optional[float]
    phone: Optional[str]
    amenities: list[str]
    next_available: Optional[str]
    min_price: Optional[float]


@router.get("", response_model=list[CourseOut])
def list_courses():
    if is_supabase_rest_configured():
        return [_row_to_course(r) for r in list_supabase_courses()]

    with get_connection() as conn:
        rows = conn.execute(LIST_COURSES).fetchall()
    return [_row_to_course(r) for r in rows]


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int):
    if is_supabase_rest_configured():
        row = get_supabase_course(course_id)
        if row:
            return _row_to_course(row)

    with get_connection() as conn:
        row = conn.execute(GET_COURSE_BY_ID, {"course_id": course_id}).fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Course not found.")
    return _row_to_course(row)


def _row_to_course(row) -> CourseOut:
    amenities = []
    if row["amenities"]:
        try:
            amenities = json.loads(row["amenities"])
        except Exception:
            pass
    return CourseOut(
        id=row["id"],
        name=row["name"],
        location=row["location"],
        holes=row["holes"] or 18,
        par=row["par"],
        rating=float(row["rating"]) if row["rating"] is not None else None,
        phone=row["phone"],
        amenities=amenities,
        next_available=row["next_available"] if "next_available" in row.keys() else None,
        min_price=float(row["min_price"]) if "min_price" in row.keys() and row["min_price"] is not None else None,
    )
