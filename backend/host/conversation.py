"""Conversation state manager with pluggable storage backends."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

try:  # pragma: no cover - exercised only when redis backend is enabled
    import redis
except ImportError:  # pragma: no cover - local dev can stay memory-only
    redis = None


SYSTEM_PROMPT = """You are a friendly and knowledgeable golf course reservation assistant. Your name is GolfBot.

You help users:
1. **Find tee times** - Search for available slots by date, time, course, and number of players.
2. **Make reservations** - Book tee times (creates a pending hold, then confirm).
3. **Manage bookings** - View, confirm, or cancel existing reservations.
4. **Get course info** - Provide details about golf courses (amenities, par, rating, etc.).
5. **Suggest alternatives** - When a slot is unavailable, offer nearby courses or different times.
6. **Check weather** - Explain forecast conditions for a course/date/time and whether they are good for golf.
7. **Recommend best options** - Suggest the best tee times based on weather, value, and availability.

## Behavior Guidelines
- Always be enthusiastic about golf! Use golf-related emoji occasionally.
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
- Format prices as JPY (for example, `JPY 12,500` or `¥12,500`).
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


class ConversationBackend(Protocol):
    def create_session(self, session_id: str, system_prompt: str) -> None: ...

    def get_history(self, session_id: str, system_prompt: str) -> list[dict]: ...

    def save_history(self, session_id: str, history: list[dict]) -> None: ...

    def get_state(self, session_id: str) -> dict[str, Any]: ...

    def save_state(self, session_id: str, state: dict[str, Any]) -> None: ...

    def session_exists(self, session_id: str) -> bool: ...

    def delete_session(self, session_id: str) -> None: ...


class MemoryConversationBackend:
    def __init__(self):
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}
        self._session_state: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, system_prompt: str) -> None:
        self._conversations[session_id] = [{"role": "system", "content": system_prompt}]
        self._session_state[session_id] = {}

    def get_history(self, session_id: str, system_prompt: str) -> list[dict]:
        if session_id not in self._conversations:
            self.create_session(session_id, system_prompt)
        return self._conversations[session_id]

    def save_history(self, session_id: str, history: list[dict]) -> None:
        self._conversations[session_id] = history

    def get_state(self, session_id: str) -> dict[str, Any]:
        self._session_state.setdefault(session_id, {})
        return self._session_state[session_id]

    def save_state(self, session_id: str, state: dict[str, Any]) -> None:
        self._session_state[session_id] = state

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._conversations

    def delete_session(self, session_id: str) -> None:
        self._conversations.pop(session_id, None)
        self._session_state.pop(session_id, None)


class RedisConversationBackend:
    def __init__(self, redis_url: str):
        if redis is None:
            raise RuntimeError(
                "Redis conversation backend requested, but the 'redis' package is not installed."
            )
        self._client = redis.from_url(redis_url, decode_responses=True)

    def _history_key(self, session_id: str) -> str:
        return f"conversation:{session_id}:history"

    def _state_key(self, session_id: str) -> str:
        return f"conversation:{session_id}:state"

    def create_session(self, session_id: str, system_prompt: str) -> None:
        self._client.set(self._history_key(session_id), json.dumps([{"role": "system", "content": system_prompt}]))
        self._client.set(self._state_key(session_id), json.dumps({}))

    def get_history(self, session_id: str, system_prompt: str) -> list[dict]:
        raw = self._client.get(self._history_key(session_id))
        if raw is None:
            self.create_session(session_id, system_prompt)
            raw = self._client.get(self._history_key(session_id)) or "[]"
        return json.loads(raw)

    def save_history(self, session_id: str, history: list[dict]) -> None:
        self._client.set(self._history_key(session_id), json.dumps(history))

    def get_state(self, session_id: str) -> dict[str, Any]:
        raw = self._client.get(self._state_key(session_id))
        return json.loads(raw) if raw else {}

    def save_state(self, session_id: str, state: dict[str, Any]) -> None:
        self._client.set(self._state_key(session_id), json.dumps(state))

    def session_exists(self, session_id: str) -> bool:
        return bool(self._client.exists(self._history_key(session_id)))

    def delete_session(self, session_id: str) -> None:
        self._client.delete(self._history_key(session_id), self._state_key(session_id))


_backend: Optional[ConversationBackend] = None
_backend_signature: Optional[tuple[str, Optional[str]]] = None


def _build_system_prompt() -> str:
    now = datetime.now()
    return SYSTEM_PROMPT.format(
        now=now.strftime("%A, %B %d, %Y at %H:%M"),
        current_time=now.strftime("%H:%M"),
    )


def _backend_config() -> tuple[str, Optional[str]]:
    backend_name = (os.getenv("CONVERSATION_BACKEND") or "memory").strip().lower()
    redis_url = os.getenv("REDIS_URL")
    return backend_name, redis_url


def _get_backend() -> ConversationBackend:
    global _backend, _backend_signature

    signature = _backend_config()
    if _backend is not None and signature == _backend_signature:
        return _backend

    backend_name, redis_url = signature
    if backend_name == "memory":
        _backend = MemoryConversationBackend()
    elif backend_name == "redis":
        _backend = RedisConversationBackend(redis_url or "redis://localhost:6379/0")
    else:
        raise ValueError(
            f"Unsupported conversation backend '{backend_name}'. Use 'memory' or 'redis'."
        )

    _backend_signature = signature
    return _backend


def _get_history(session_id: str) -> list[dict]:
    return _get_backend().get_history(session_id, _build_system_prompt())


def _get_state(session_id: str) -> dict[str, Any]:
    _get_history(session_id)
    return _get_backend().get_state(session_id)


def _save_state(session_id: str, state: dict[str, Any]) -> None:
    _get_backend().save_state(session_id, state)


def create_session() -> str:
    session_id = str(uuid.uuid4())
    _get_backend().create_session(session_id, _build_system_prompt())
    return session_id


def get_history(session_id: str) -> list[dict]:
    return _get_history(session_id)


def add_message(session_id: str, role: str, content: str, **kwargs) -> None:
    history = list(_get_history(session_id))
    history.append({"role": role, "content": content, **kwargs})
    _get_backend().save_history(session_id, history)


def add_tool_call(session_id: str, tool_call_message: dict) -> None:
    history = list(_get_history(session_id))
    history.append(tool_call_message)
    _get_backend().save_history(session_id, history)


def add_tool_result(session_id: str, tool_call_id: str, content: str) -> None:
    history = list(_get_history(session_id))
    history.append({
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    })
    _get_backend().save_history(session_id, history)


def session_exists(session_id: str) -> bool:
    return _get_backend().session_exists(session_id)


def get_pending_confirmation(session_id: str) -> Optional[dict]:
    return _get_state(session_id).get("pending_confirmation")


def get_active_context(session_id: str) -> dict:
    state = dict(_get_state(session_id))
    if "active_context" not in state:
        state["active_context"] = {}
        _save_state(session_id, state)
    return state["active_context"]


def update_active_context(session_id: str, updates: dict) -> dict:
    state = dict(_get_state(session_id))
    context = dict(state.get("active_context") or {})
    for key, value in updates.items():
        if value is not None:
            context[key] = value
    state["active_context"] = context
    _save_state(session_id, state)
    return context


def set_pending_confirmation(session_id: str, details: dict) -> None:
    state = dict(_get_state(session_id))
    state["pending_confirmation"] = details
    _save_state(session_id, state)


def clear_pending_confirmation(session_id: str) -> None:
    state = dict(_get_state(session_id))
    state.pop("pending_confirmation", None)
    _save_state(session_id, state)


def delete_session(session_id: str) -> None:
    _get_backend().delete_session(session_id)
