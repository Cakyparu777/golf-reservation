"""Persistent MCP client connection for the host application."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("host.mcp_client")

SERVER_MODULE = "backend.mcp_server.server"


class MCPClient:
    """Manages a persistent connection to the Golf Reservation MCP server."""

    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._stdio_context = None
        self._session_context = None
        self._openai_tool_cache: Optional[list[dict[str, Any]]] = None
        self._disable_tool_cache = os.getenv("MCP_DISABLE_TOOL_CACHE", "0").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self._connection_lock = asyncio.Lock()
        self._tool_lock = asyncio.Lock()

    async def startup(self) -> None:
        """Start the MCP subprocess and initialize a persistent session."""
        await self._ensure_connected()

    async def shutdown(self) -> None:
        """Close the persistent MCP session and subprocess."""
        async with self._connection_lock:
            await self._close_connection()

    async def list_openai_tools(self) -> list[dict[str, Any]]:
        """Discover MCP tools and convert them to OpenAI tool definitions."""
        if not self._disable_tool_cache and self._openai_tool_cache is not None:
            return self._openai_tool_cache

        async with self._tool_lock:
            if not self._disable_tool_cache and self._openai_tool_cache is not None:
                return self._openai_tool_cache

            session = await self._ensure_connected()
            try:
                result = await session.list_tools()
            except Exception:
                await self._handle_connection_failure("tool discovery")
                raise

            tools = getattr(result, "tools", None)
            if tools is None and hasattr(result, "model_dump"):
                tools = result.model_dump().get("tools", [])

            if not tools:
                raise RuntimeError("MCP server returned no tools during discovery.")

            discovered_tools = [self._normalize_tool_definition(tool) for tool in tools]
            if not self._disable_tool_cache:
                self._openai_tool_cache = discovered_tools
            logger.info("Discovered %s MCP tools.", len(discovered_tools))
            return discovered_tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Call an MCP tool and return the result as a JSON string."""
        logger.info("Calling MCP tool: %s(%s)", tool_name, arguments)

        async with self._tool_lock:
            session = await self._ensure_connected()
            try:
                result = await session.call_tool(tool_name, arguments=arguments)
            except Exception as exc:
                logger.error("Tool %s failed: %s", tool_name, exc)
                await self._handle_connection_failure(f"tool call '{tool_name}'")
                return json.dumps({"error": f"Tool execution failed: {str(exc)}"})

        if result.content:
            text_parts = []
            for block in result.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
            content = "\n".join(text_parts) if text_parts else str(result.content)
        else:
            content = "{}"

        logger.info("Tool %s returned: %s...", tool_name, content[:200])
        return content

    def clear_tool_cache(self) -> None:
        """Clear cached tool discovery results."""
        self._openai_tool_cache = None

    async def _ensure_connected(self) -> ClientSession:
        if self._session is not None:
            return self._session

        async with self._connection_lock:
            if self._session is not None:
                return self._session

            project_root = str(Path(__file__).resolve().parents[2])
            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", SERVER_MODULE],
                cwd=project_root,
            )

            self._stdio_context = stdio_client(server_params)
            try:
                read_stream, write_stream = await self._stdio_context.__aenter__()
                self._session_context = ClientSession(read_stream, write_stream)
                session = await self._session_context.__aenter__()
                await session.initialize()
                self._session = session
            except Exception:
                await self._close_connection()
                raise

            logger.info("Persistent MCP client connected and initialized.")
            return self._session

    async def _handle_connection_failure(self, context: str) -> None:
        logger.warning("Resetting MCP connection after failure during %s.", context)
        async with self._connection_lock:
            await self._close_connection()

    async def _close_connection(self) -> None:
        session_context = self._session_context
        stdio_context = self._stdio_context
        self._session = None
        self._session_context = None
        self._stdio_context = None
        self._openai_tool_cache = None

        if session_context is not None:
            try:
                await session_context.__aexit__(None, None, None)
            except Exception as exc:
                logger.warning("Failed to close MCP session cleanly: %s", exc)

        if stdio_context is not None:
            try:
                await stdio_context.__aexit__(None, None, None)
            except Exception as exc:
                logger.warning("Failed to close MCP stdio client cleanly: %s", exc)

    def _normalize_tool_definition(self, tool: Any) -> dict[str, Any]:
        if hasattr(tool, "model_dump"):
            payload = tool.model_dump(by_alias=True)
        elif isinstance(tool, dict):
            payload = dict(tool)
        else:
            payload = {
                "name": getattr(tool, "name", None),
                "description": getattr(tool, "description", ""),
                "inputSchema": getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None),
            }

        name = payload.get("name")
        if not name:
            raise RuntimeError(f"Received invalid MCP tool payload: {payload}")

        return {
            "type": "function",
            "function": {
                "name": name,
                "description": payload.get("description") or "",
                "parameters": payload.get("inputSchema")
                or payload.get("input_schema")
                or {"type": "object", "properties": {}},
            },
        }
