"""Conversation state manager.

Stores conversation history in-memory keyed by session ID.
For v1/demo purposes only — swap to Redis or DB for production.
"""

from __future__ import annotations

import uuid
from datetime import datetime


from typing import Any, Dict, List, Optional

# In-memory store: session_id → list of message dicts
_conversations: Dict[str, List[Dict]] = {}
_session_state: Dict[str, Dict[str, Any]] = {}

# System prompt that defines the chatbot's personality and capabilities
SYSTEM_PROMPT = """You are a friendly and knowledgeable golf course reservation assistant. Your name is GolfBot.

You help users:
1. **Find tee times** — Search for available slots by date, time, course, and number of players.
2. **Make reservations** — Book tee times (creates a pending hold, then confirm).
3. **Manage bookings** — View, confirm, or cancel existing reservations.
4. **Get course info** — Provide details about golf courses (amenities, par, rating, etc.).
5. **Suggest alternatives** — When a slot is unavailable, offer nearby courses or different times.
6. **Check weather** — Explain forecast conditions for a course/date/time and whether they are good for golf.
7. **Recommend best options** — Suggest the best tee times based on weather, value, and availability.

## Behavior Guidelines
- Always be enthusiastic about golf! Use golf-related emoji (⛳🏌️) occasionally.
- When searching for tee times, you MUST have at least a **date** and **number of players**. Ask for these if the user hasn't provided them.
- If the user provides a specific date, time, and course for a booking/search request, first restate those details and ask for confirmation before calling any search or reservation tool.
- After finding tee times, present them as a numbered list with key details (time, price, course).
- When making a reservation, you need: tee_time_id, user_name, user_email, and num_players. Ask for any missing info.
- After creating a reservation, always ask the user to **confirm** before finalizing.
- When date, time, and course are known, use weather information to tell the user whether conditions look good, mixed, or bad for golf.
- If a pending reservation tool result includes a weather re-check, mention it clearly before asking the user to finalize the booking.
- If the user asks for recommendations, best options, or good-weather choices, prefer weather-aware recommendations instead of a plain search.
- Default preference for all users: avoid rainy conditions and avoid wind above 20 km/h unless the user explicitly says they are okay with that.
- If a saved home area, travel mode, or max travel time is available, use it automatically instead of asking again.
- Format prices as USD (e.g., $125.00).
- If the user's request is ambiguous, ask a clarifying question rather than guessing.
- Keep responses concise but informative.

## Current Date & Time
The current date and time is: {now}
Use this for all relative references ("today", "tomorrow", "this weekend", etc.).

## IMPORTANT: Past Tee Time Rule
NEVER suggest or book a tee time that is in the past.
When searching for today's tee times, always set time_range_start to at least the current time ({current_time}).
If a user asks for "the earliest available" today, use {current_time} as the minimum time_range_start.
"""


def _build_system_prompt() -> str:
    now = datetime.now()
    return SYSTEM_PROMPT.format(
        now=now.strftime("%A, %B %d, %Y at %H:%M"),
        current_time=now.strftime("%H:%M"),
    )


def create_session() -> str:
    """Create a new conversation session and return its ID."""
    session_id = str(uuid.uuid4())
    _conversations[session_id] = [
        {"role": "system", "content": _build_system_prompt()}
    ]
    _session_state[session_id] = {}
    return session_id


def get_history(session_id: str) -> list[dict]:
    """Get the full message history for a session.

    Creates a new session if the ID doesn't exist.
    """
    if session_id not in _conversations:
        _conversations[session_id] = [
            {"role": "system", "content": _build_system_prompt()}
        ]
        _session_state[session_id] = {}
    return _conversations[session_id]


def add_message(session_id: str, role: str, content: str, **kwargs) -> None:
    """Append a message to the conversation history."""
    history = get_history(session_id)
    message = {"role": role, "content": content, **kwargs}
    history.append(message)


def add_tool_call(session_id: str, tool_call_message: dict) -> None:
    """Append an assistant message containing tool calls."""
    history = get_history(session_id)
    history.append(tool_call_message)


def add_tool_result(session_id: str, tool_call_id: str, content: str) -> None:
    """Append a tool result message."""
    history = get_history(session_id)
    history.append({
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    })


def session_exists(session_id: str) -> bool:
    """Check if a session exists."""
    return session_id in _conversations


def get_pending_confirmation(session_id: str) -> Optional[dict]:
    """Return pending booking confirmation details for a session."""
    get_history(session_id)
    return _session_state.get(session_id, {}).get("pending_confirmation")


def get_active_context(session_id: str) -> dict:
    """Return structured active context for a session."""
    get_history(session_id)
    return _session_state.setdefault(session_id, {}).setdefault("active_context", {})


def update_active_context(session_id: str, updates: dict) -> dict:
    """Merge non-null updates into the session's active context."""
    context = dict(get_active_context(session_id))
    for key, value in updates.items():
        if value is not None:
            context[key] = value
    _session_state.setdefault(session_id, {})["active_context"] = context
    return context


def set_pending_confirmation(session_id: str, details: dict) -> None:
    """Store pending booking confirmation details for a session."""
    get_history(session_id)
    _session_state.setdefault(session_id, {})["pending_confirmation"] = details


def clear_pending_confirmation(session_id: str) -> None:
    """Clear pending booking confirmation details for a session."""
    get_history(session_id)
    _session_state.setdefault(session_id, {}).pop("pending_confirmation", None)


def delete_session(session_id: str) -> None:
    """Delete a session and free memory."""
    _conversations.pop(session_id, None)
    _session_state.pop(session_id, None)
