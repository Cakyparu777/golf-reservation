"""Pydantic schemas for the FastAPI endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    message: str = Field(..., min_length=1, max_length=2000, description="The user's message.")
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID to continue a conversation. "
                    "Omit or set to null to start a new session.",
    )
    user_name: Optional[str] = Field(default=None, description="User's name for bookings.")
    user_email: Optional[str] = Field(default=None, description="User's email for bookings.")


class ChatResponse(BaseModel):
    """Chat response returned to the user."""
    reply: str = Field(..., description="The assistant's response.")
    session_id: str = Field(..., description="Session ID for continuing the conversation.")
    tool_calls_made: list[str] = Field(
        default_factory=list,
        description="Names of MCP tools invoked during this turn (for debugging).",
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "0.1.0"
