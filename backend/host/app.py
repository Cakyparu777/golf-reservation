"""FastAPI application — Golf Reservation Chatbot Host.

This is the main entry point. It exposes a /chat endpoint that:
1. Receives a user message
2. Sends it to OpenAI with tool definitions
3. If OpenAI requests tool calls, routes them through the MCP client
4. Returns the final assistant response

Run with:
    uvicorn backend.host.app:app --reload
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import conversation
from .auth import get_current_access_token, get_current_auth_payload, get_current_user_id, is_supabase_auth_payload
from .confirmation import (
    build_confirmation_prompt,
    build_confirmation_system_note,
    is_affirmative_response,
    is_negative_response,
    merge_booking_details,
    should_request_confirmation,
)
from .llm import LLMClient, ToolCallParseError
from .mcp_client import MCPClient
from .schemas import ChatRequest, ChatResponse, HealthResponse
from .routes.auth_router import router as auth_router
from .routes.courses_router import router as courses_router
from .routes.recommendations_router import router as recommendations_router
from .routes.tee_times_router import router as tee_times_router
from .routes.reservations_router import router as reservations_router
from .routes.weather_router import router as weather_router
from .session_context import (
    build_context_system_note,
    extract_message_context,
    extract_context_from_assistant_reply,
    extract_context_from_tool_result,
    is_nearest_course_request,
    resolve_context,
)
from backend.mcp_server.db.connection import get_connection
from backend.mcp_server.db.queries import GET_USER_BY_ID
from backend.services.course_discovery import find_nearest_courses
from backend.services.supabase import get_or_create_user_profile, is_supabase_rest_configured
from backend.services.weather import get_weather_forecast

# Load environment variables
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("host.app")


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _load_authenticated_profile_context(
    user_id: int,
    auth_payload: dict,
    access_token: str,
) -> dict[str, Optional[str] | int]:
    if is_supabase_auth_payload(auth_payload) and is_supabase_rest_configured():
        profile = get_or_create_user_profile(access_token, auth_payload)
        return {
            "user_name": profile.get("name"),
            "user_email": profile.get("email"),
            "home_area": profile.get("home_area"),
            "travel_mode": profile.get("travel_mode"),
            "max_travel_minutes": profile.get("max_travel_minutes"),
        }

    with get_connection() as conn:
        user = conn.execute(GET_USER_BY_ID, {"user_id": user_id}).fetchone()

    if not user:
        return {}

    return {
        "user_name": user["name"],
        "user_email": user["email"],
        "home_area": user["home_area"],
        "travel_mode": user["travel_mode"],
        "max_travel_minutes": user["max_travel_minutes"],
    }


def _profile_context_from_active_session(active_context: dict, user_email: Optional[str]) -> Optional[dict]:
    if not active_context.get("profile_context_loaded"):
        return None
    if user_email and active_context.get("authenticated_user_email") != user_email:
        return None
    return {
        "user_name": active_context.get("authenticated_user_name"),
        "user_email": active_context.get("authenticated_user_email"),
        "home_area": active_context.get("home_area"),
        "travel_mode": active_context.get("travel_mode"),
        "max_travel_minutes": active_context.get("max_travel_minutes"),
    }


def _profile_context_from_request(request: ChatRequest, auth_payload: dict) -> Optional[dict]:
    if not all(
        value is not None
        for value in (request.home_area, request.travel_mode, request.max_travel_minutes)
    ):
        return None

    metadata = auth_payload.get("user_metadata") or {}
    email = str(auth_payload.get("email") or request.user_email or "").strip() or None
    name = (
        request.user_name
        or metadata.get("full_name")
        or metadata.get("name")
        or (email.split("@", 1)[0] if email else None)
    )
    return {
        "user_name": name,
        "user_email": email,
        "home_area": request.home_area,
        "travel_mode": request.travel_mode,
        "max_travel_minutes": request.max_travel_minutes,
    }


def _resolve_profile_context(
    request: ChatRequest,
    auth_payload: dict,
    access_token: str,
    user_id: int,
    active_context: dict,
) -> dict[str, Optional[str] | int]:
    auth_email = str(auth_payload.get("email") or request.user_email or "").strip() or None

    request_context = _profile_context_from_request(request, auth_payload)
    if request_context is not None:
        return request_context

    cached_context = _profile_context_from_active_session(active_context, auth_email)
    if cached_context is not None:
        return cached_context

    return _load_authenticated_profile_context(user_id, auth_payload, access_token)


def _authenticated_user_context(request: ChatRequest, auth_payload: dict, profile_context: dict) -> dict[str, Optional[str]]:
    metadata = auth_payload.get("user_metadata") or {}
    email = str(
        request.user_email
        or profile_context.get("user_email")
        or auth_payload.get("email")
        or ""
    ).strip() or None
    name = (
        request.user_name
        or profile_context.get("user_name")
        or metadata.get("full_name")
        or metadata.get("name")
        or (email.split("@", 1)[0] if email else None)
    )
    return {"user_name": name, "user_email": email}


def _build_weather_context(details: dict) -> Optional[dict]:
    if not all(details.get(field) for field in ("course_name", "date", "time")):
        return None

    try:
        return get_weather_forecast(
            course_name=details["course_name"],
            date=details["date"],
            time=details["time"],
        )
    except Exception as exc:
        logger.warning("Weather lookup failed during confirmation prompt: %s", exc)
        return {"error": "weather service unavailable"}


def _augment_tool_result_with_weather(tool_name: str, result: str) -> str:
    if tool_name != "tool_make_reservation":
        return result

    try:
        payload = json.loads(result)
    except json.JSONDecodeError:
        return result

    if payload.get("error"):
        return result

    reservation = payload.get("reservation") or {}
    course_name = reservation.get("course_name")
    tee_datetime = reservation.get("tee_datetime")
    if not course_name or not tee_datetime:
        return result

    try:
        tee_dt = datetime.fromisoformat(tee_datetime)
        weather = get_weather_forecast(
            course_name=course_name,
            date=tee_dt.strftime("%Y-%m-%d"),
            time=tee_dt.strftime("%H:%M"),
        )
    except Exception as exc:
        logger.warning("Weather lookup failed after reservation creation: %s", exc)
        weather = {"error": "weather service unavailable"}

    payload["weather_check"] = weather
    if weather.get("message"):
        payload["message"] = f"{payload.get('message', '').strip()} Weather re-check: {weather['message']}".strip()

    return json.dumps(payload)


def _parse_tool_payload(result: str) -> dict:
    try:
        payload = json.loads(result)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _should_clear_pending_reservation_id(tool_name: str, payload: dict) -> bool:
    if tool_name not in {"tool_confirm_reservation", "tool_cancel_reservation"}:
        return False
    if not payload.get("error"):
        return True

    error = str(payload.get("error") or "").lower()
    return any(fragment in error for fragment in ("already confirmed", "already cancelled", "expired", "not found"))


def _apply_tool_result_context(session_id: str, tool_name: str, tool_args: dict, result: str) -> None:
    payload = _parse_tool_payload(result)
    conversation.update_active_context(
        session_id,
        extract_context_from_tool_result(
            tool_name,
            tool_args,
            result,
            conversation.get_active_context(session_id),
        ),
    )
    if _should_clear_pending_reservation_id(tool_name, payload):
        conversation.clear_active_context_keys(session_id, "pending_reservation_id")


def _build_nearest_course_reply(payload: dict) -> str:
    nearest_courses = payload.get("nearest_courses") or []
    user_area = payload.get("user_area") or "your area"
    travel_mode = payload.get("travel_mode") or "your preferred mode"

    if not nearest_courses:
        return (
            f"I couldn't find a nearby golf course for {user_area} within your current travel preferences. "
            "If you want, I can widen the search or use another area."
        )

    top = nearest_courses[0]
    lines = [f"The nearest golf course to {user_area} is {top['name']} in {top['location']}."]
    if top.get("travel_minutes") is not None:
        lines.append(f"Estimated travel time is about {top['travel_minutes']} minutes by {travel_mode}.")

    if len(nearest_courses) > 1:
        lines.append("Other nearby options:")
        for index, course in enumerate(nearest_courses[1:], start=2):
            suffix = f" - about {course['travel_minutes']} minutes" if course.get("travel_minutes") is not None else ""
            lines.append(f"{index}. {course['name']} ({course['location']}){suffix}")

    lines.append("If you want, I can also recommend the best tee times near there. ⛳")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

llm_client: Optional[LLMClient] = None
mcp_client: Optional[MCPClient] = None


# ---------------------------------------------------------------------------
# App Lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize clients on startup, clean up on shutdown."""
    global llm_client, mcp_client

    # Ensure the SQLite fallback is initialized for local development/tests.
    if not is_supabase_rest_configured():
        from backend.db.seed_data import seed_database

        seed_database()

    llm_client = LLMClient()
    mcp_client = MCPClient()
    await mcp_client.startup()
    logger.info("✅ Host initialized. LLM and MCP clients ready.")

    yield

    if mcp_client:
        await mcp_client.shutdown()
    logger.info("Shutting down host.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Golf Reservation Chatbot",
    description="A conversational chatbot for booking golf tee times, powered by MCP and OpenAI.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(recommendations_router)
app.include_router(tee_times_router)
app.include_router(reservations_router)
app.include_router(weather_router)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    auth_payload: dict = Depends(get_current_auth_payload),
    access_token: str = Depends(get_current_access_token),
    user_id: int = Depends(get_current_user_id),
):
    """Main chat endpoint.

    Accepts a user message, orchestrates LLM ↔ MCP tool calls,
    and returns the assistant's final response.
    """
    if not llm_client or not mcp_client:
        raise HTTPException(status_code=503, detail="Service not ready.")

    # Resolve or create session
    session_id = request.session_id or conversation.create_session()
    if request.session_id and not conversation.session_exists(request.session_id):
        session_id = conversation.create_session()

    active_context = conversation.get_active_context(session_id)
    profile_context = _resolve_profile_context(
        request,
        auth_payload,
        access_token,
        user_id,
        active_context,
    )
    authenticated_user = _authenticated_user_context(request, auth_payload, profile_context)

    # Store user context if provided
    if authenticated_user["user_name"]:
        conversation.add_message(
            session_id, "system",
            f"The user's name is {authenticated_user['user_name']}."
            + (f" Their email is {authenticated_user['user_email']}." if authenticated_user["user_email"] else ""),
        )

    profile_updates = {
        "home_area": request.home_area or profile_context.get("home_area"),
        "travel_mode": request.travel_mode or profile_context.get("travel_mode"),
        "max_travel_minutes": request.max_travel_minutes or profile_context.get("max_travel_minutes"),
        "authenticated_user_email": authenticated_user["user_email"],
        "authenticated_user_name": authenticated_user["user_name"],
        "profile_context_loaded": True,
    }
    conversation.update_active_context(session_id, profile_updates)

    # Add user message to history
    conversation.add_message(session_id, "user", request.message)

    resolved_context = resolve_context(request.message, conversation.get_active_context(session_id))
    resolved_context = conversation.update_active_context(session_id, resolved_context)
    explicit_message_context = extract_message_context(request.message)

    if (
        is_nearest_course_request(request.message)
        and resolved_context.get("location")
        and not resolved_context.get("date")
        and not resolved_context.get("num_players")
    ):
        nearest_result = find_nearest_courses(
            user_area=str(resolved_context["location"]),
            travel_mode=str(resolved_context.get("travel_mode") or "train"),
            max_travel_minutes=resolved_context.get("max_travel_minutes"),
            max_results=3,
        )
        nearest_result["travel_mode"] = resolved_context.get("travel_mode") or "train"
        reply = _build_nearest_course_reply(nearest_result)
        conversation.add_message(session_id, "assistant", reply)
        return ChatResponse(reply=reply, session_id=session_id, tool_calls_made=[])

    pending_confirmation = conversation.get_pending_confirmation(session_id)
    current_details = {
        "course_name": resolved_context.get("course_name") or resolved_context.get("active_course_name"),
        "date": resolved_context.get("date"),
        "time": resolved_context.get("time"),
        "num_players": resolved_context.get("num_players"),
    }
    explicit_details = {
        "course_name": explicit_message_context.get("course_name"),
        "date": explicit_message_context.get("date"),
        "time": explicit_message_context.get("time"),
        "num_players": explicit_message_context.get("num_players"),
    }
    merged_details = merge_booking_details(pending_confirmation, current_details)

    if pending_confirmation and resolved_context.get("intent") == "weather":
        pass
    elif pending_confirmation and is_affirmative_response(request.message):
        conversation.clear_pending_confirmation(session_id)
        conversation.add_message(
            session_id,
            "system",
            build_confirmation_system_note(merged_details),
        )
    elif pending_confirmation and (is_negative_response(request.message) or any(explicit_details.values())):
        conversation.clear_pending_confirmation(session_id)
        if should_request_confirmation(request.message, merged_details, pending_exists=True):
            reply = build_confirmation_prompt(merged_details, _build_weather_context(merged_details))
            conversation.set_pending_confirmation(session_id, merged_details)
            conversation.add_message(session_id, "assistant", reply)
            return ChatResponse(reply=reply, session_id=session_id, tool_calls_made=[])

        if is_negative_response(request.message) and not any(explicit_details.values()):
            reply = "No problem. Tell me the date, time, course, or player count you want to change, and I'll update it."
            conversation.add_message(session_id, "assistant", reply)
            return ChatResponse(reply=reply, session_id=session_id, tool_calls_made=[])

    elif should_request_confirmation(request.message, merged_details):
        reply = build_confirmation_prompt(merged_details, _build_weather_context(merged_details))
        conversation.set_pending_confirmation(session_id, merged_details)
        conversation.add_message(session_id, "assistant", reply)
        return ChatResponse(reply=reply, session_id=session_id, tool_calls_made=[])

    pending_reservation_id = conversation.get_active_context(session_id).get("pending_reservation_id")
    if pending_reservation_id and is_affirmative_response(request.message):
        result = await mcp_client.call_tool(
            "tool_confirm_reservation",
            {"reservation_id": pending_reservation_id},
        )
        payload = _parse_tool_payload(result)
        _apply_tool_result_context(
            session_id,
            "tool_confirm_reservation",
            {"reservation_id": pending_reservation_id},
            result,
        )
        reply = str(payload.get("message") or payload.get("error") or "Reservation confirmation failed.")
        conversation.add_message(session_id, "assistant", reply)
        return ChatResponse(
            reply=reply,
            session_id=session_id,
            tool_calls_made=["tool_confirm_reservation"],
        )

    # Get conversation history
    reply = "I'm sorry, I couldn't generate a response."
    tool_calls_made: list[str] = []
    max_iterations = 5  # Safety limit for tool-call loops

    openai_tools = await mcp_client.list_openai_tools()

    for iteration in range(max_iterations):
        history = conversation.get_history(session_id)
        context_note = build_context_system_note(conversation.get_active_context(session_id))
        request_history = history + ([{"role": "system", "content": context_note}] if context_note else [])

        # Call OpenAI
        assistant_message = llm_client.chat(request_history, openai_tools)

        # Check if the LLM wants to call tools
        try:
            tool_calls = llm_client.parse_tool_calls(assistant_message)
        except ToolCallParseError as exc:
            logger.error("Malformed tool call returned by LLM: %s", exc)
            raise HTTPException(
                status_code=502,
                detail="The language model returned an invalid tool call.",
            ) from exc

        if not tool_calls:
            # No tool calls — we have the final response
            reply = assistant_message.content or "I'm sorry, I couldn't generate a response."
            conversation.add_message(session_id, "assistant", reply)
            conversation.update_active_context(
                session_id,
                extract_context_from_assistant_reply(reply, conversation.get_active_context(session_id)),
            )
            break
        else:
            # Add the assistant's tool-call message to history
            conversation.add_tool_call(session_id, assistant_message.model_dump())

            # Execute each tool call via MCP
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_call_id = tc["id"]

                tool_calls_made.append(tool_name)
                logger.info(f"Tool call [{iteration+1}]: {tool_name}({tool_args})")

                # Call the MCP tool
                result = await mcp_client.call_tool(tool_name, tool_args)
                result = _augment_tool_result_with_weather(tool_name, result)

                # Add tool result to conversation
                conversation.add_tool_result(session_id, tool_call_id, result)
                _apply_tool_result_context(session_id, tool_name, tool_args, result)

    else:
        # max_iterations exceeded
        reply = (
            "I'm sorry, I'm having trouble processing your request. "
            "Could you try rephrasing it?"
        )
        conversation.add_message(session_id, "assistant", reply)

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        tool_calls_made=tool_calls_made,
    )
