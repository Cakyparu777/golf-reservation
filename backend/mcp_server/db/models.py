"""Pydantic models for database entities.

These models serve as the interface between raw SQL rows and
the rest of the application. They also define the shapes returned
by MCP tools.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReservationStatus(str, Enum):
    """Possible states for a reservation."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------

class GolfCourse(BaseModel):
    """A golf course."""
    id: int
    name: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    holes: int = 18
    par: Optional[int] = None
    rating: Optional[float] = None
    phone: Optional[str] = None
    amenities: Optional[str] = None  # JSON string
    created_at: Optional[str] = None


class TeeTime(BaseModel):
    """An available tee-time slot."""
    id: int
    course_id: int
    tee_datetime: str
    max_players: int = 4
    available_slots: int
    price_per_player: float
    is_active: bool = True
    created_at: Optional[str] = None

    # Joined fields (populated by search queries)
    course_name: Optional[str] = None
    course_location: Optional[str] = None


class User(BaseModel):
    """A registered user."""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    created_at: Optional[str] = None


class Reservation(BaseModel):
    """A tee-time reservation."""
    id: int
    tee_time_id: int
    user_id: int
    num_players: int
    total_price: float
    status: ReservationStatus = ReservationStatus.PENDING
    confirmation_number: Optional[str] = None
    hold_expires_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Joined fields (populated by list queries)
    course_name: Optional[str] = None
    tee_datetime: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class ReservationHistory(BaseModel):
    """Audit log entry for reservation status changes."""
    id: int
    reservation_id: int
    old_status: Optional[str] = None
    new_status: str
    reason: Optional[str] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Tool Response Wrappers
# ---------------------------------------------------------------------------

class SearchResult(BaseModel):
    """Response shape for search_tee_times."""
    available_tee_times: list[TeeTime]
    total_results: int


class AlternativeSuggestion(BaseModel):
    """Response shape for suggest_alternatives."""
    nearby_courses: list[TeeTime] = Field(default_factory=list)
    alternative_times: list[TeeTime] = Field(default_factory=list)
    message: str = ""


class ReservationResult(BaseModel):
    """Response shape for reservation actions."""
    reservation: Reservation
    message: str
