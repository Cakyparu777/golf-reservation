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
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import conversation
from .llm import LLMClient
from .mcp_client import MCPClient
from .schemas import ChatRequest, ChatResponse, HealthResponse
from .routes.auth_router import router as auth_router
from .routes.courses_router import router as courses_router
from .routes.tee_times_router import router as tee_times_router
from .routes.reservations_router import router as reservations_router

# Load environment variables
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("host.app")

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

    # Ensure DB is initialized and seeded
    from backend.db.seed_data import seed_database
    seed_database()

    llm_client = LLMClient()
    mcp_client = MCPClient()
    logger.info("✅ Host initialized. LLM and MCP clients ready.")

    yield

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
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(tee_times_router)
app.include_router(reservations_router)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
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

    # Store user context if provided
    if request.user_name:
        conversation.add_message(
            session_id, "system",
            f"The user's name is {request.user_name}."
            + (f" Their email is {request.user_email}." if request.user_email else ""),
        )

    # Add user message to history
    conversation.add_message(session_id, "user", request.message)

    # Get conversation history
    history = conversation.get_history(session_id)

    tool_calls_made: list[str] = []
    max_iterations = 5  # Safety limit for tool-call loops

    async with mcp_client.connect() as mcp_session:
        for iteration in range(max_iterations):
            # Call OpenAI
            assistant_message = llm_client.chat(history)

            # Check if the LLM wants to call tools
            tool_calls = llm_client.parse_tool_calls(assistant_message)

            if not tool_calls:
                # No tool calls — we have the final response
                reply = assistant_message.content or "I'm sorry, I couldn't generate a response."
                conversation.add_message(session_id, "assistant", reply)
                break
            else:
                # Add the assistant's tool-call message to history
                history.append(assistant_message.model_dump())

                # Execute each tool call via MCP
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["arguments"]
                    tool_call_id = tc["id"]

                    tool_calls_made.append(tool_name)
                    logger.info(f"Tool call [{iteration+1}]: {tool_name}({tool_args})")

                    # Call the MCP tool
                    result = await mcp_client.call_tool(mcp_session, tool_name, tool_args)

                    # Add tool result to conversation
                    conversation.add_tool_result(session_id, tool_call_id, result)
                    history = conversation.get_history(session_id)

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
