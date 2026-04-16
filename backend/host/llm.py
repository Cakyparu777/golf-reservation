"""OpenAI LLM client wrapper.

Handles communication with the OpenAI Chat Completions API,
including tool definitions and the tool-call loop.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger("host.llm")

# ---------------------------------------------------------------------------
# Tool Definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "tool_search_tee_times",
            "description": (
                "Search for available tee times at golf courses. "
                "Find open slots based on date, time window, number of players, "
                "and optionally a specific course name (partial match supported)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Desired date in YYYY-MM-DD format.",
                    },
                    "num_players": {
                        "type": "integer",
                        "description": "Number of players (1-4).",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Optional partial or full course name to filter by.",
                    },
                    "time_range_start": {
                        "type": "string",
                        "description": 'Earliest acceptable tee time in HH:MM format. Default "06:00".',
                    },
                    "time_range_end": {
                        "type": "string",
                        "description": 'Latest acceptable tee time in HH:MM format. Default "18:00".',
                    },
                },
                "required": ["date", "num_players"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_course_info",
            "description": (
                "Get detailed information about a golf course including location, "
                "par, rating, phone, and amenities. "
                "Provide either course_id or course_name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "integer",
                        "description": "Exact course ID for lookup.",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Partial or full course name for fuzzy lookup.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_weather_forecast",
            "description": (
                "Get forecast weather for a golf course at a specific date and time. "
                "Use it to tell the user whether the conditions look good, mixed, or bad for golf."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "Partial or full course name.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Requested date in YYYY-MM-DD format.",
                    },
                    "time": {
                        "type": "string",
                        "description": "Requested tee time in HH:MM format.",
                    },
                },
                "required": ["course_name", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_suggest_alternatives",
            "description": (
                "Suggest alternative tee times or nearby courses when a slot is unavailable. "
                "Returns available slots at nearby courses and alternative times at the original course."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Originally requested date (YYYY-MM-DD).",
                    },
                    "time_range_start": {
                        "type": "string",
                        "description": "Originally requested start time (HH:MM).",
                    },
                    "num_players": {
                        "type": "integer",
                        "description": "Number of players (1-4).",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Original course name for alternative time search.",
                    },
                    "latitude": {
                        "type": "number",
                        "description": "User's latitude for nearby course search.",
                    },
                    "longitude": {
                        "type": "number",
                        "description": "User's longitude for nearby course search.",
                    },
                    "radius_km": {
                        "type": "integer",
                        "description": "Search radius in km (default 50).",
                    },
                },
                "required": ["date", "time_range_start", "num_players"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_recommend_tee_times",
            "description": (
                "Recommend the best tee times based on weather, value, and availability. "
                "Use this when the user asks for the best option, good-weather choices, or suggestions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Requested date in YYYY-MM-DD format.",
                    },
                    "num_players": {
                        "type": "integer",
                        "description": "Number of players (1-4).",
                    },
                    "preferred_time": {
                        "type": "string",
                        "enum": ["morning", "afternoon", "evening"],
                        "description": "Optional preferred time of day.",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Optional partial or full course name filter.",
                    },
                    "user_area": {
                        "type": "string",
                        "description": "Optional user home area or nearest station for nearest-course ranking.",
                    },
                    "travel_mode": {
                        "type": "string",
                        "enum": ["train", "car", "either"],
                        "description": "Optional travel mode preference from the user profile.",
                    },
                    "max_travel_minutes": {
                        "type": "integer",
                        "description": "Optional max preferred travel time in minutes.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of recommendations to return.",
                    },
                },
                "required": ["date", "num_players"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_make_reservation",
            "description": (
                "Create a pending reservation for a tee time. "
                "The reservation is held for 10 minutes and must be confirmed. "
                "Requires tee_time_id from search results, user details, and player count."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tee_time_id": {
                        "type": "integer",
                        "description": "The ID of the tee time to book (from search results).",
                    },
                    "user_name": {
                        "type": "string",
                        "description": "Full name for the booking.",
                    },
                    "user_email": {
                        "type": "string",
                        "description": "Email address for confirmation.",
                    },
                    "num_players": {
                        "type": "integer",
                        "description": "Number of players (1-4).",
                    },
                    "user_phone": {
                        "type": "string",
                        "description": "Optional phone number.",
                    },
                },
                "required": ["tee_time_id", "user_name", "user_email", "num_players"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_confirm_reservation",
            "description": (
                "Confirm a pending reservation to finalize the booking. "
                "Must be called within 10 minutes of making the reservation. "
                "Returns a confirmation number on success."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {
                        "type": "integer",
                        "description": "The ID of the pending reservation to confirm.",
                    },
                },
                "required": ["reservation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_cancel_reservation",
            "description": (
                "Cancel an existing reservation (pending or confirmed). "
                "The tee time slot will be released back to the pool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {
                        "type": "integer",
                        "description": "The ID of the reservation to cancel.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for cancellation.",
                    },
                },
                "required": ["reservation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_list_user_reservations",
            "description": (
                "List all reservations for a user by their email address. "
                "Can filter by status: PENDING, CONFIRMED, CANCELLED, EXPIRED, or ALL."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_email": {
                        "type": "string",
                        "description": "The user's email address.",
                    },
                    "status_filter": {
                        "type": "string",
                        "description": "Filter by status: PENDING, CONFIRMED, CANCELLED, EXPIRED, or ALL (default ALL).",
                        "enum": ["PENDING", "CONFIRMED", "CANCELLED", "EXPIRED", "ALL"],
                    },
                },
                "required": ["user_email"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

class LLMClient:
    """Wrapper around OpenAI Chat Completions with tool-call support."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

    def chat(self, messages: list[dict]) -> Any:
        """Send messages to OpenAI and return the response.

        Args:
            messages: Conversation history including system prompt.

        Returns:
            The raw response message dict from OpenAI.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            tools=TOOL_DEFINITIONS,  # type: ignore[arg-type]
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message

    def parse_tool_calls(self, message) -> list[dict]:
        """Extract tool calls from an assistant message.

        Returns:
            List of dicts with 'id', 'name', and 'arguments' keys.
        """
        if not message.tool_calls:
            return []

        calls = []
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse tool arguments: {tc.function.arguments}")
                args = {}

            calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "arguments": args,
            })

        return calls
