"""Supabase data access helpers for the production runtime path."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
import os
from typing import Any, Optional

import httpx


def _supabase_url() -> Optional[str]:
    return (
        os.getenv("SUPABASE_URL")
        or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        or os.getenv("VITE_SUPABASE_URL")
        or ""
    ).rstrip("/") or None


def _publishable_key() -> Optional[str]:
    return (
        os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )


def _service_role_key() -> Optional[str]:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def is_supabase_rest_configured() -> bool:
    return bool(_supabase_url() and _publishable_key())


def is_supabase_service_role_configured() -> bool:
    return bool(_supabase_url() and _service_role_key())


def is_supabase_subject(payload: dict) -> bool:
    subject = str(payload.get("sub") or "")
    return bool(subject) and not subject.isdigit()


def _headers(
    user_token: Optional[str] = None,
    *,
    service_role: bool = False,
    upsert: bool = False,
) -> dict[str, str]:
    key = _service_role_key() if service_role else _publishable_key()
    if not key:
        raise RuntimeError("Supabase configuration is missing required API keys.")

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {user_token or key}",
    }
    if upsert:
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    return headers


def _request(
    method: str,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    json: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    user_token: Optional[str] = None,
    service_role: bool = False,
    upsert: bool = False,
) -> httpx.Response:
    base_url = _supabase_url()
    if not base_url:
        raise RuntimeError("Supabase URL is not configured.")

    response = httpx.request(
        method,
        f"{base_url}/rest/v1/{path}",
        params=params,
        json=json,
        headers=_headers(user_token, service_role=service_role, upsert=upsert),
        timeout=15.0,
    )
    response.raise_for_status()
    return response


def _rpc(function_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = _request(
        "POST",
        f"rpc/{function_name}",
        json=payload,
        service_role=True,
    )
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected RPC response from {function_name}: {data}")
    return data


def _date_bounds(date_str: str) -> tuple[str, str]:
    day = datetime.fromisoformat(date_str).date()
    start = datetime.combine(day, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _parse_rows(response: httpx.Response) -> list[dict[str, Any]]:
    data = response.json()
    return data if isinstance(data, list) else [data]


def _single_row(response: httpx.Response) -> Optional[dict[str, Any]]:
    rows = _parse_rows(response)
    return rows[0] if rows else None


def list_courses() -> list[dict[str, Any]]:
    response = _request(
        "GET",
        "course_summaries",
        params={"select": "*", "order": "rating.desc.nullslast"},
    )
    return _parse_rows(response)


def get_course(course_id: int) -> Optional[dict[str, Any]]:
    response = _request(
        "GET",
        "course_summaries",
        params={"select": "*", "id": f"eq.{course_id}", "limit": "1"},
    )
    return _single_row(response)


def get_course_by_name(course_name: str) -> Optional[dict[str, Any]]:
    response = _request(
        "GET",
        "golf_courses",
        params={
            "select": "*",
            "name": f"ilike.*{course_name}*",
            "limit": "1",
            "order": "rating.desc.nullslast",
        },
    )
    return _single_row(response)


def get_course_coordinates(course_id: int) -> tuple[Optional[float], Optional[float]]:
    response = _request(
        "GET",
        "golf_courses",
        params={"select": "latitude,longitude", "id": f"eq.{course_id}", "limit": "1"},
    )
    row = _single_row(response) or {}
    return row.get("latitude"), row.get("longitude")


def list_tee_times(*, course_id: Optional[int], num_players: int, limit: int) -> list[dict[str, Any]]:
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
    return _parse_rows(response)


def get_tee_time(tee_time_id: int) -> Optional[dict[str, Any]]:
    response = _request(
        "GET",
        "tee_time_public",
        params={"select": "*", "id": f"eq.{tee_time_id}", "limit": "1"},
    )
    return _single_row(response)


def search_tee_times(
    *,
    date: str,
    num_players: int,
    course_name: Optional[str] = None,
    time_range_start: str = "06:00",
    time_range_end: str = "18:00",
    limit: int = 20,
) -> list[dict[str, Any]]:
    start_of_day, end_of_day = _date_bounds(date)
    params = {
        "select": "*",
        "available_slots": f"gte.{num_players}",
        "is_active": "eq.true",
        "and": f"(tee_datetime.gte.{start_of_day},tee_datetime.lt.{end_of_day})",
        "order": "tee_datetime.asc",
        "limit": str(max(limit, 50)),
    }
    if course_name:
        params["course_name"] = f"ilike.*{course_name}*"

    rows = _parse_rows(_request("GET", "tee_time_public", params=params))

    filtered: list[dict[str, Any]] = []
    for row in rows:
        tee_time = datetime.fromisoformat(row["tee_datetime"])
        tee_clock = tee_time.strftime("%H:%M")
        if tee_clock < time_range_start or tee_clock > time_range_end:
            continue
        if tee_time <= datetime.now(UTC) and date == datetime.now(UTC).strftime("%Y-%m-%d"):
            continue
        filtered.append(row)

    return filtered[:limit]


def list_alternative_tee_times(
    *,
    date: str,
    num_players: int,
    course_name: str,
    time_range_start: str,
    time_range_end: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    day = datetime.fromisoformat(date).date()
    start = datetime.combine(day - timedelta(days=1), time.min, tzinfo=UTC)
    end = datetime.combine(day + timedelta(days=2), time.min, tzinfo=UTC)
    rows = _parse_rows(
        _request(
            "GET",
            "tee_time_public",
            params={
                "select": "*",
                "available_slots": f"gte.{num_players}",
                "is_active": "eq.true",
                "course_name": f"ilike.*{course_name}*",
                "and": f"(tee_datetime.gte.{start.isoformat()},tee_datetime.lt.{end.isoformat()})",
                "order": "tee_datetime.asc",
                "limit": "100",
            },
        )
    )

    filtered: list[dict[str, Any]] = []
    for row in rows:
        tee_dt = datetime.fromisoformat(row["tee_datetime"])
        tee_date = tee_dt.strftime("%Y-%m-%d")
        tee_clock = tee_dt.strftime("%H:%M")
        if tee_date == date and time_range_start <= tee_clock <= time_range_end:
            continue
        if tee_date == datetime.now(UTC).strftime("%Y-%m-%d") and tee_dt <= datetime.now(UTC):
            continue
        filtered.append(row)

    return filtered[:limit]


def list_reservations_for_email(user_email: str, status_filter: Optional[str] = None) -> list[dict[str, Any]]:
    params = {
        "select": "*",
        "user_email": f"eq.{user_email}",
        "order": "tee_datetime.desc",
    }
    if status_filter and status_filter.upper() != "ALL":
        params["status"] = f"eq.{status_filter.upper()}"

    response = _request(
        "GET",
        "reservation_details",
        params=params,
        service_role=True,
    )
    return _parse_rows(response)


def list_my_reservations(user_token: str) -> list[dict[str, Any]]:
    response = _request(
        "GET",
        "reservation_details",
        params={"select": "*", "order": "tee_datetime.desc"},
        user_token=user_token,
    )
    return _parse_rows(response)


def get_my_reservation(user_token: str, reservation_id: int) -> Optional[dict[str, Any]]:
    response = _request(
        "GET",
        "reservation_details",
        params={"select": "*", "id": f"eq.{reservation_id}", "limit": "1"},
        user_token=user_token,
    )
    return _single_row(response)


def upsert_user_profile(user_token: str, payload: dict, overrides: Optional[dict] = None) -> dict:
    metadata = payload.get("user_metadata") or {}
    email = str(payload.get("email") or "")
    auth_user_id = str(payload.get("sub") or "")
    if not email or not auth_user_id:
        raise RuntimeError("Supabase payload is missing user identifiers.")

    row = {
        "auth_user_id": auth_user_id,
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
    result = response.json()
    if isinstance(result, list):
        return result[0]
    return result


def get_or_create_user_profile(user_token: str, payload: dict) -> dict:
    response = _request(
        "GET",
        "users",
        params={"select": "*", "auth_user_id": f"eq.{payload.get('sub')}", "limit": "1"},
        user_token=user_token,
    )
    row = _single_row(response)
    if row:
        return row
    return upsert_user_profile(user_token, payload)


def make_reservation(
    *,
    tee_time_id: int,
    user_name: str,
    user_email: str,
    num_players: int,
    user_phone: Optional[str] = None,
    auth_user_id: Optional[str] = None,
) -> dict[str, Any]:
    return _rpc(
        "create_pending_reservation",
        {
            "p_tee_time_id": tee_time_id,
            "p_user_name": user_name,
            "p_user_email": user_email,
            "p_num_players": num_players,
            "p_user_phone": user_phone,
            "p_auth_user_id": auth_user_id,
        },
    )


def confirm_reservation(reservation_id: int) -> dict[str, Any]:
    return _rpc("confirm_pending_reservation", {"p_reservation_id": reservation_id})


def cancel_reservation(reservation_id: int, reason: Optional[str] = None) -> dict[str, Any]:
    return _rpc(
        "cancel_existing_reservation",
        {"p_reservation_id": reservation_id, "p_reason": reason},
    )
