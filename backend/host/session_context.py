"""Structured session context and follow-up resolution helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Optional

from backend.mcp_server.db.connection import get_connection

WEATHER_KEYWORDS = ("weather", "forecast", "rain", "wind", "temperature", "sunny", "cloudy")
BOOKING_KEYWORDS = ("book", "reserve", "hold", "confirm", "tee time", "slot")
RECOMMENDATION_KEYWORDS = ("best", "recommend", "suggest", "good weather", "closest", "nearest")
FOLLOW_UP_COURSE_REFS = ("there", "that course", "that one", "the course", "it")
FOLLOW_UP_DATE_REFS = ("that day", "that date", "same day")
FOLLOW_UP_TIME_REFS = ("same time", "that time")
ORDINAL_WORDS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "fourth": 4,
    "4th": 4,
    "fifth": 5,
    "5th": 5,
}
COURSE_STOP_WORDS = {"golf", "course", "club", "country", "links"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _course_aliases(name: str) -> set[str]:
    normalized = _normalize(name)
    aliases = {normalized}
    tokens = [token for token in normalized.split() if token not in COURSE_STOP_WORDS]
    if tokens:
        aliases.add(" ".join(tokens))
    return {alias for alias in aliases if alias}


def _list_course_names() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT name FROM golf_courses ORDER BY name ASC").fetchall()
    return [row["name"] for row in rows]


def _extract_course_mentions(text: str) -> list[str]:
    normalized = _normalize(text)
    matches: list[tuple[int, str]] = []
    for course_name in _list_course_names():
        for alias in _course_aliases(course_name):
            position = normalized.find(alias)
            if alias and position >= 0:
                matches.append((position, course_name))
                break

    matches.sort(key=lambda item: item[0])
    ordered: list[str] = []
    for _, course_name in matches:
        if course_name not in ordered:
            ordered.append(course_name)
    return ordered


def _extract_date(message: str, now: datetime) -> Optional[str]:
    lowered = message.lower()
    if "tomorrow" in lowered:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in lowered:
        return now.strftime("%Y-%m-%d")

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


def _extract_players(message: str) -> dict:
    lowered = message.lower()
    range_match = re.search(r"\b(\d)\s*[-/]\s*(\d)\s*players?\b", lowered)
    if range_match:
        first = int(range_match.group(1))
        second = int(range_match.group(2))
        low = min(first, second)
        high = max(first, second)
        return {"num_players_min": low, "num_players_max": high, "num_players": high}

    or_match = re.search(r"\b(\d)\s*(?:or)\s*(\d)\s*players?\b", lowered)
    if or_match:
        first = int(or_match.group(1))
        second = int(or_match.group(2))
        low = min(first, second)
        high = max(first, second)
        return {"num_players_min": low, "num_players_max": high, "num_players": high}

    single_match = re.search(r"\bfor\s+(\d)\b", lowered) or re.search(r"\b(\d)\s+(?:players?|people|golfers?)\b", lowered)
    if single_match:
        count = int(single_match.group(1))
        if 1 <= count <= 4:
            return {"num_players_min": count, "num_players_max": count, "num_players": count}

    return {}


def _extract_location(message: str) -> Optional[str]:
    match = re.search(r"\b(?:nearest to|near|around|close to)\s+([a-zA-Z0-9\-\s]+)", message, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip(" .,!?")


def _extract_option_reference(message: str) -> Optional[int]:
    lowered = message.lower()
    numeric_match = re.search(r"\b(?:option|slot|one)?\s*(\d+)(?:st|nd|rd|th)?\b", lowered)
    if numeric_match and ("option" in lowered or "slot" in lowered or "one" in lowered):
        return int(numeric_match.group(1))

    for word, value in ORDINAL_WORDS.items():
        if word in lowered:
            return value

    return None


def _detect_intent(message: str) -> Optional[str]:
    lowered = message.lower()
    if any(keyword in lowered for keyword in WEATHER_KEYWORDS):
        return "weather"
    if any(keyword in lowered for keyword in BOOKING_KEYWORDS):
        return "booking"
    if any(keyword in lowered for keyword in RECOMMENDATION_KEYWORDS):
        return "recommendation"
    if "course" in lowered or "courses" in lowered:
        return "course_info"
    return None


def extract_message_context(message: str, now: Optional[datetime] = None) -> dict:
    """Extract structured context from a user or assistant message."""
    current_time = now or datetime.now()
    course_mentions = _extract_course_mentions(message)
    context = {
        "course_name": course_mentions[0] if course_mentions else None,
        "course_mentions": course_mentions,
        "date": _extract_date(message, current_time),
        "time": _extract_time(message),
        "location": _extract_location(message),
        "intent": _detect_intent(message),
        "selected_option_index": _extract_option_reference(message),
    }
    context.update(_extract_players(message))
    return context


def _message_has_any(message: str, phrases: tuple[str, ...]) -> bool:
    lowered = message.lower()
    return any(phrase in lowered for phrase in phrases)


def resolve_context(message: str, current_context: Optional[dict] = None, now: Optional[datetime] = None) -> dict:
    """Resolve follow-up references against the current session context."""
    existing = dict(current_context or {})
    extracted = extract_message_context(message, now=now)
    resolved = dict(existing)

    if extracted.get("location"):
        resolved["location"] = extracted["location"]

    option_index = extracted.get("selected_option_index")
    if option_index and existing.get("last_presented_options"):
        for option in existing["last_presented_options"]:
            if option.get("index") == option_index:
                resolved["selected_option_index"] = option_index
                resolved["course_name"] = option.get("course_name") or resolved.get("course_name")
                resolved["active_course_name"] = resolved.get("course_name") or resolved.get("active_course_name")
                resolved["date"] = option.get("date") or resolved.get("date")
                resolved["time"] = option.get("time") or resolved.get("time")
                resolved["selected_tee_time_id"] = option.get("tee_time_id")
                break

    if extracted.get("course_name"):
        resolved["course_name"] = extracted["course_name"]
        resolved["active_course_name"] = extracted["course_name"]
    elif _message_has_any(message, FOLLOW_UP_COURSE_REFS) or extracted.get("intent") == "weather":
        if existing.get("active_course_name"):
            resolved["course_name"] = existing["active_course_name"]

    if extracted.get("date"):
        resolved["date"] = extracted["date"]
    elif _message_has_any(message, FOLLOW_UP_DATE_REFS) or extracted.get("intent") == "weather":
        if existing.get("date"):
            resolved["date"] = existing["date"]

    if extracted.get("time"):
        resolved["time"] = extracted["time"]
    elif _message_has_any(message, FOLLOW_UP_TIME_REFS) or extracted.get("intent") == "weather":
        if existing.get("time"):
            resolved["time"] = existing["time"]

    for key in ("num_players", "num_players_min", "num_players_max"):
        if extracted.get(key) is not None:
            resolved[key] = extracted[key]

    if extracted.get("intent"):
        resolved["intent"] = extracted["intent"]

    if extracted.get("selected_option_index"):
        resolved["selected_option_index"] = extracted["selected_option_index"]

    return resolved


def _extract_presented_options(reply: str, context: dict) -> list[dict]:
    course_name = context.get("active_course_name") or context.get("course_name")
    date = context.get("date")
    if not course_name or not date:
        return []

    options: list[dict] = []
    pattern = re.compile(r"(?:^|\n)\s*(\d+)\.\s+\*\*?([0-9: ]+(?:AM|PM))\*\*?", re.IGNORECASE)
    for match in pattern.finditer(reply):
        index = int(match.group(1))
        raw_time = match.group(2).strip()
        time = _extract_time(raw_time)
        if not time:
            continue
        options.append({
            "index": index,
            "course_name": course_name,
            "date": date,
            "time": time,
        })
    return options


def extract_context_from_assistant_reply(reply: str, current_context: Optional[dict] = None) -> dict:
    """Extract context updates from an assistant reply."""
    existing = dict(current_context or {})
    updates: dict = {}
    course_mentions = _extract_course_mentions(reply)
    if len(course_mentions) == 1:
        updates["course_name"] = course_mentions[0]
        updates["active_course_name"] = course_mentions[0]
    elif course_mentions and not existing.get("active_course_name"):
        updates["active_course_name"] = course_mentions[0]

    merged = {**existing, **updates}
    options = _extract_presented_options(reply, merged)
    if options:
        updates["last_presented_options"] = options
        if not updates.get("active_course_name") and options[0].get("course_name"):
            updates["active_course_name"] = options[0]["course_name"]

    return updates


def extract_context_from_tool_result(tool_name: str, tool_args: dict, result: str, current_context: Optional[dict] = None) -> dict:
    """Extract context updates from a tool result payload."""
    existing = dict(current_context or {})
    updates: dict = {}

    try:
        payload = json.loads(result)
    except json.JSONDecodeError:
        payload = {}

    if tool_name in {"tool_search_tee_times", "tool_recommend_tee_times"}:
        updates["date"] = tool_args.get("date") or existing.get("date")
        if tool_args.get("time_range_start"):
            updates["time"] = tool_args.get("time_range_start")
        if tool_args.get("num_players") is not None:
            updates["num_players"] = tool_args.get("num_players")
            updates["num_players_min"] = tool_args.get("num_players")
            updates["num_players_max"] = tool_args.get("num_players")

    if tool_name == "tool_search_tee_times":
        tee_times = payload.get("available_tee_times", [])
        if tee_times:
            first_course = tee_times[0].get("course_name")
            if first_course:
                updates["active_course_name"] = first_course
                updates["course_name"] = first_course
            updates["last_presented_options"] = [
                {
                    "index": index + 1,
                    "tee_time_id": tee_time.get("id"),
                    "course_name": tee_time.get("course_name"),
                    "date": datetime.fromisoformat(tee_time["tee_datetime"]).strftime("%Y-%m-%d"),
                    "time": datetime.fromisoformat(tee_time["tee_datetime"]).strftime("%H:%M"),
                }
                for index, tee_time in enumerate(tee_times[:10])
            ]
            if not updates.get("time"):
                updates["time"] = datetime.fromisoformat(tee_times[0]["tee_datetime"]).strftime("%H:%M")

    elif tool_name == "tool_recommend_tee_times":
        recommendations = payload.get("recommended_tee_times", [])
        if recommendations:
            top = recommendations[0]["tee_time"]
            updates["active_course_name"] = top.get("course_name")
            updates["course_name"] = top.get("course_name")
            updates["last_presented_options"] = [
                {
                    "index": index + 1,
                    "tee_time_id": item["tee_time"].get("id"),
                    "course_name": item["tee_time"].get("course_name"),
                    "date": datetime.fromisoformat(item["tee_time"]["tee_datetime"]).strftime("%Y-%m-%d"),
                    "time": datetime.fromisoformat(item["tee_time"]["tee_datetime"]).strftime("%H:%M"),
                }
                for index, item in enumerate(recommendations[:10])
            ]

    elif tool_name == "tool_get_weather_forecast":
        if not payload.get("error"):
            updates["active_course_name"] = payload.get("course_name") or existing.get("active_course_name")
            updates["course_name"] = payload.get("course_name") or existing.get("course_name")
            if payload.get("requested_datetime"):
                requested_dt = datetime.fromisoformat(payload["requested_datetime"])
                updates["date"] = requested_dt.strftime("%Y-%m-%d")
                updates["time"] = requested_dt.strftime("%H:%M")

    elif tool_name == "tool_get_course_info":
        if not payload.get("error") and payload.get("name"):
            updates["active_course_name"] = payload["name"]
            updates["course_name"] = payload["name"]

    elif tool_name == "tool_make_reservation":
        reservation = payload.get("reservation", {})
        if reservation:
            updates["pending_reservation_id"] = reservation.get("id")
            updates["active_course_name"] = reservation.get("course_name") or existing.get("active_course_name")
            updates["course_name"] = updates.get("active_course_name")
            if reservation.get("tee_datetime"):
                tee_dt = datetime.fromisoformat(reservation["tee_datetime"])
                updates["date"] = tee_dt.strftime("%Y-%m-%d")
                updates["time"] = tee_dt.strftime("%H:%M")

    elif tool_name == "tool_confirm_reservation":
        updates["pending_reservation_id"] = None

    return updates


def build_context_system_note(context: Optional[dict]) -> Optional[str]:
    """Build a compact system note that summarizes active session context."""
    if not context:
        return None

    lines = ["Resolved session context for this turn:"]
    useful = 0

    if context.get("location"):
        useful += 1
        lines.append(f"- User area/location: {context['location']}")
    if context.get("home_area"):
        useful += 1
        lines.append(f"- Saved home area: {context['home_area']}")
    if context.get("travel_mode"):
        useful += 1
        lines.append(f"- Saved travel mode: {context['travel_mode']}")
    if context.get("max_travel_minutes"):
        useful += 1
        lines.append(f"- Max preferred travel time: {context['max_travel_minutes']} minutes")
    if context.get("active_course_name") or context.get("course_name"):
        useful += 1
        lines.append(f"- Active course: {context.get('active_course_name') or context.get('course_name')}")
    if context.get("date"):
        useful += 1
        lines.append(f"- Active date: {context['date']}")
    if context.get("time"):
        useful += 1
        lines.append(f"- Active time: {context['time']}")
    if context.get("num_players"):
        useful += 1
        if context.get("num_players_min") and context.get("num_players_max") and context["num_players_min"] != context["num_players_max"]:
            lines.append(
                f"- Party size range: {context['num_players_min']}-{context['num_players_max']} players; use {context['num_players']} players for availability checks unless the user says otherwise"
            )
        else:
            lines.append(f"- Party size: {context['num_players']} players")
    if context.get("selected_option_index"):
        useful += 1
        lines.append(f"- The user referenced option #{context['selected_option_index']}")
    if context.get("last_presented_options"):
        useful += 1
        lines.append(f"- There are {len(context['last_presented_options'])} recently presented options available for follow-up references like 'the second one'")
    if context.get("intent"):
        useful += 1
        lines.append(f"- Current likely intent: {context['intent']}")

    if useful == 0:
        return None

    lines.append("- Default preference: avoid rainy tee times and avoid wind above 20 km/h unless the user explicitly says otherwise")
    lines.append("Use this context to resolve follow-up references like 'there', 'that day', 'same time', or 'the second one'. Do not ask the user to repeat these details unless they are still ambiguous.")
    return "\n".join(lines)
