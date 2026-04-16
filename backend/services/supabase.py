"""Supabase REST helpers for incremental runtime migration."""

from __future__ import annotations

from datetime import UTC, datetime
import os
from typing import Optional

import httpx


def _supabase_url() -> Optional[str]:
    return (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/") or None


def _supabase_key() -> Optional[str]:
    return os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")


def is_supabase_rest_configured() -> bool:
    return bool(_supabase_url() and _supabase_key())


def _headers(user_token: Optional[str] = None, *, upsert: bool = False) -> dict[str, str]:
    key = _supabase_key()
    if not key:
        raise RuntimeError("Supabase REST configuration is missing.")

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {user_token or key}",
    }
    if upsert:
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    return headers


def _request(method: str, path: str, *, params: Optional[dict] = None, json: Optional[dict | list] = None, user_token: Optional[str] = None, upsert: bool = False) -> httpx.Response:
    base_url = _supabase_url()
    if not base_url:
        raise RuntimeError("Supabase REST configuration is missing.")

    response = httpx.request(
        method,
        f"{base_url}/rest/v1/{path}",
        params=params,
        json=json,
        headers=_headers(user_token, upsert=upsert),
        timeout=10.0,
    )
    response.raise_for_status()
    return response


def list_courses() -> list[dict]:
    response = _request(
        "GET",
        "course_summaries",
        params={"select": "*", "order": "rating.desc.nullslast"},
    )
    return response.json()


def get_course(course_id: int) -> Optional[dict]:
    response = _request(
        "GET",
        "course_summaries",
        params={"select": "*", "id": f"eq.{course_id}", "limit": "1"},
    )
    rows = response.json()
    return rows[0] if rows else None


def list_tee_times(*, course_id: Optional[int], num_players: int, limit: int) -> list[dict]:
    params = {
        "select": "*",
        "available_slots": f"gte.{num_players}",
        "is_active": "eq.true",
        "tee_datetime": f"gt.{datetime.now(UTC).isoformat()}",
        "order": "tee_datetime.asc",
        "limit": str(limit),
    }
    if course_id is not None:
        params["course_id"] = f"eq.{course_id}"

    response = _request("GET", "tee_time_public", params=params)
    return response.json()


def is_supabase_subject(payload: dict) -> bool:
    subject = str(payload.get("sub") or "")
    return bool(subject) and not subject.isdigit()


def upsert_user_profile(user_token: str, payload: dict, overrides: Optional[dict] = None) -> dict:
    metadata = payload.get("user_metadata") or {}
    email = str(payload.get("email") or "")
    if not email:
        raise RuntimeError("Supabase payload is missing email.")

    row = {
        "auth_user_id": str(payload.get("sub")),
        "email": email,
        "name": (overrides or {}).get("name") or metadata.get("full_name") or metadata.get("name") or email.split("@", 1)[0],
        "phone": (overrides or {}).get("phone", metadata.get("phone") or payload.get("phone")),
        "home_area": (overrides or {}).get("home_area"),
        "travel_mode": (overrides or {}).get("travel_mode") or "train",
        "max_travel_minutes": (overrides or {}).get("max_travel_minutes") or 60,
    }

    response = _request(
        "POST",
        "users",
        params={"on_conflict": "auth_user_id", "select": "*"},
        json=row,
        user_token=user_token,
        upsert=True,
    )
    rows = response.json()
    return rows[0] if isinstance(rows, list) else rows


def get_or_create_user_profile(user_token: str, payload: dict) -> dict:
    response = _request(
        "GET",
        "users",
        params={"select": "*", "auth_user_id": f"eq.{payload.get('sub')}", "limit": "1"},
        user_token=user_token,
    )
    rows = response.json()
    if rows:
        return rows[0]
    return upsert_user_profile(user_token, payload)
