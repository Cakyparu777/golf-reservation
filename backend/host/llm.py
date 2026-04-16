"""OpenAI LLM client wrapper."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger("host.llm")


class ToolCallParseError(ValueError):
    """Raised when the LLM returns an invalid tool call payload."""


def _read_attr(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


class LLMClient:
    """Wrapper around OpenAI Chat Completions with tool-call support."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

    def chat(self, messages: list[dict], tools: list[dict[str, Any]]) -> Any:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message

    def parse_tool_calls(self, message: Any) -> list[dict[str, Any]]:
        tool_calls = _read_attr(message, "tool_calls")
        if not tool_calls:
            return []

        parsed_calls: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            function = _read_attr(tool_call, "function")
            tool_call_id = _read_attr(tool_call, "id")
            tool_name = _read_attr(function, "name")
            raw_arguments = _read_attr(function, "arguments")

            if not tool_call_id or not tool_name:
                raise ToolCallParseError("Tool call is missing an id or function name.")

            if not isinstance(raw_arguments, str) or not raw_arguments.strip():
                raise ToolCallParseError(
                    f"Tool call '{tool_name}' is missing JSON arguments."
                )

            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                logger.error("Failed to parse tool arguments for %s: %s", tool_name, raw_arguments)
                raise ToolCallParseError(
                    f"Tool call '{tool_name}' returned malformed JSON arguments."
                ) from exc

            if not isinstance(arguments, dict):
                raise ToolCallParseError(
                    f"Tool call '{tool_name}' must use a JSON object for arguments."
                )

            parsed_calls.append(
                {
                    "id": tool_call_id,
                    "name": tool_name,
                    "arguments": arguments,
                }
            )

        return parsed_calls
