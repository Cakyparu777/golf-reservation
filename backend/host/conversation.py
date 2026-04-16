"""Conversation state manager.

Stores conversation history in-memory keyed by session ID.
For v1/demo purposes only — swap to Redis or DB for production.
"""

from __future__ import annotations

import uuid
from datetime import datetime


from typing import Dict, List

# In-memory store: session_id → list of message dicts
_conversations: Dict[str, List[Dict]] = {}

# System prompt that defines the chatbot's personality and capabilities
SYSTEM_PROMPT = """You are a friendly and knowledgeable golf course reservation assistant. Your name is GolfBot.

You help users:
1. **Find tee times** — Search for available slots by date, time, course, and number of players.
2. **Make reservations** — Book tee times (creates a pending hold, then confirm).
3. **Manage bookings** — View, confirm, or cancel existing reservations.
4. **Get course info** — Provide details about golf courses (amenities, par, rating, etc.).
5. **Suggest alternatives** — When a slot is unavailable, offer nearby courses or different times.

## Behavior Guidelines
- Always be enthusiastic about golf! Use golf-related emoji (⛳🏌️) occasionally.
- When searching for tee times, you MUST have at least a **date** and **number of players**. Ask for these if the user hasn't provided them.
- After finding tee times, present them as a numbered list with key details (time, price, course).
- When making a reservation, you need: tee_time_id, user_name, user_email, and num_players. Ask for any missing info.
- After creating a reservation, always ask the user to **confirm** before finalizing.
- Format prices as USD (e.g., $125.00).
- If the user's request is ambiguous, ask a clarifying question rather than guessing.
- Keep responses concise but informative.

## Current Date
Today is {today}. Use this as context for relative date references like "this Saturday" or "tomorrow".
"""


def create_session() -> str:
    """Create a new conversation session and return its ID."""
    session_id = str(uuid.uuid4())
    today = datetime.now().strftime("%A, %B %d, %Y")
    _conversations[session_id] = [
        {"role": "system", "content": SYSTEM_PROMPT.format(today=today)}
    ]
    return session_id


def get_history(session_id: str) -> list[dict]:
    """Get the full message history for a session.

    Creates a new session if the ID doesn't exist.
    """
    if session_id not in _conversations:
        # Treat as new session
        today = datetime.now().strftime("%A, %B %d, %Y")
        _conversations[session_id] = [
            {"role": "system", "content": SYSTEM_PROMPT.format(today=today)}
        ]
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


def delete_session(session_id: str) -> None:
    """Delete a session and free memory."""
    _conversations.pop(session_id, None)
