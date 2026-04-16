"""Helpers for structured booking confirmation prompts."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from backend.mcp_server.db.connection import get_connection

BOOKING_KEYWORDS = (
    "book",
    "booking",
    "reserve",
    "reservation",
    "tee time",
    "tee-time",
    "search",
    "find",
    "play",
)

AFFIRMATIVE_WORDS = {"yes", "y", "confirm", "confirmed", "looks good", "go ahead", "proceed", "ok", "okay"}
NEGATIVE_WORDS = {"no", "n", "change", "wrong", "incorrect", "not correct", "different"}
COURSE_STOP_WORDS = {"golf", "course", "club", "country", "links"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _contains_any_phrase(message: str, phrases: set[str]) -> bool:
    normalized = _normalize(message)
    tokens = set(normalized.split())
    for phrase in phrases:
        if " " in phrase:
            if phrase in normalized:
                return True
        elif phrase in tokens:
            return True
    return False


def _course_aliases(name: str) -> set[str]:
    normalized = _normalize(name)
    aliases = {normalized}
    tokens = [token for token in normalized.split() if token not in COURSE_STOP_WORDS]
    if tokens:
        aliases.add(" ".join(tokens))
    return {alias for alias in aliases if alias}


def _extract_course_name(message: str) -> Optional[str]:
    normalized_message = _normalize(message)
    best_match: Optional[str] = None
    best_length = -1

    with get_connection() as conn:
        courses = conn.execute("SELECT name FROM golf_courses ORDER BY name ASC").fetchall()

    for row in courses:
        course_name = row["name"]
        for alias in _course_aliases(course_name):
            if alias and alias in normalized_message and len(alias) > best_length:
                best_match = course_name
                best_length = len(alias)

    return best_match


def _extract_date(message: str, now: datetime) -> Optional[str]:
    iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", message)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        return datetime(year, month, day).strftime("%Y-%m-%d")

    slash_match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", message)
    if slash_match:
        month = int(slash_match.group(1))
        day = int(slash_match.group(2))
        year_group = slash_match.group(3)
        if year_group is None:
            year = now.year
            candidate = datetime(year, month, day)
            if candidate.date() < now.date():
                candidate = datetime(year + 1, month, day)
        else:
            year = int(year_group)
            if year < 100:
                year += 2000
            candidate = datetime(year, month, day)
        return candidate.strftime("%Y-%m-%d")

    return None


def _extract_time(message: str) -> Optional[str]:
    ampm_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", message, re.IGNORECASE)
    if ampm_match:
        hour = int(ampm_match.group(1))
        minute = int(ampm_match.group(2) or 0)
        meridiem = ampm_match.group(3).lower()
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"

    twenty_four_match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", message)
    if twenty_four_match:
        hour = int(twenty_four_match.group(1))
        minute = int(twenty_four_match.group(2))
        return f"{hour:02d}:{minute:02d}"

    return None


def _extract_num_players(message: str) -> Optional[int]:
    lowered = message.lower()
    for label, count in (("solo", 1), ("single", 1), ("twosome", 2), ("threesome", 3), ("foursome", 4)):
        if label in lowered:
            return count

    match = re.search(r"\bfor\s+(\d)\b", lowered) or re.search(r"\b(\d)\s+(?:players?|people|golfers?)\b", lowered)
    if match:
        count = int(match.group(1))
        if 1 <= count <= 4:
            return count

    return None


def extract_booking_details(message: str, now: Optional[datetime] = None) -> dict:
    """Extract structured booking details from a user message."""
    current_time = now or datetime.now()
    return {
        "date": _extract_date(message, current_time),
        "time": _extract_time(message),
        "course_name": _extract_course_name(message),
        "num_players": _extract_num_players(message),
    }


def merge_booking_details(base: Optional[dict], updates: Optional[dict]) -> dict:
    """Merge new details into an existing pending confirmation payload."""
    merged = dict(base or {})
    for key, value in (updates or {}).items():
        if value is not None:
            merged[key] = value
    return merged


def has_booking_intent(message: str) -> bool:
    """Return True when the message looks like a tee-time search/booking request."""
    lowered = message.lower()
    return any(keyword in lowered for keyword in BOOKING_KEYWORDS)


def has_core_booking_details(details: dict) -> bool:
    """Return True when date, time, and course are all present."""
    return all(details.get(field) for field in ("date", "time", "course_name"))


def should_request_confirmation(message: str, details: dict, *, pending_exists: bool = False) -> bool:
    """Return True when the app should ask the user to confirm booking details."""
    if not has_core_booking_details(details):
        return False
    return pending_exists or has_booking_intent(message)


def is_affirmative_response(message: str) -> bool:
    """Return True when the user confirmed the pending details."""
    return _contains_any_phrase(message, AFFIRMATIVE_WORDS)


def is_negative_response(message: str) -> bool:
    """Return True when the user rejected the pending details."""
    return _contains_any_phrase(message, NEGATIVE_WORDS)


def build_confirmation_prompt(details: dict, weather: Optional[dict] = None) -> str:
    """Build a compact confirmation prompt for the chat UI."""
    lines = [
        "I found these booking details:",
        f"- Date: {details['date']}",
        f"- Time: {details['time']}",
        f"- Golf course: {details['course_name']}",
    ]

    if details.get("num_players"):
        lines.append(f"- Players: {details['num_players']}")

    if weather and not weather.get("error"):
        lines.append(f"- Weather: {weather['message']}")
    elif weather and weather.get("error"):
        lines.append(f"- Weather: unavailable right now ({weather['error']})")

    lines.append("Can you confirm these details?")
    lines.append("Reply 'yes' to confirm or tell me what to change.")
    return "\n".join(lines)


def build_confirmation_system_note(details: dict) -> str:
    """Build a system note so the LLM knows the user confirmed the details."""
    note = (
        "The user confirmed these booking details: "
        f"date={details.get('date')}, time={details.get('time')}, "
        f"course_name={details.get('course_name')}"
    )
    if details.get("num_players"):
        note += f", num_players={details['num_players']}"
    note += ". Proceed with the request using these confirmed details unless the user changes them."
    return note
