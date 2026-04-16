"""MCP Client — connects to the MCP server via stdio.

Spawns the MCP server as a subprocess and communicates using the
official MCP Python SDK's ClientSession over stdio transport.
"""

from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("host.mcp_client")

# Path to the MCP server module
SERVER_MODULE = "backend.mcp_server.server"


class MCPClient:
    """Manages a connection to the Golf Reservation MCP server."""

    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._stdio_context = None
        self._session_context = None
        self._openai_tool_cache: Optional[list[dict[str, Any]]] = None

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[ClientSession, None]:
        """Context manager that spawns the MCP server and yields a session.

        Usage:
            client = MCPClient()
            async with client.connect() as session:
                result = await session.call_tool("tool_search_tee_times", {...})
        """
        # The server is a Python module, run it as a subprocess
        project_root = str(Path(__file__).resolve().parents[2])
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", SERVER_MODULE],
            cwd=project_root,
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.info("MCP client connected and initialized.")
                yield session

    async def call_tool(self, session: ClientSession, tool_name: str, arguments: dict[str, Any]) -> str:
        """Call an MCP tool and return the result as a JSON string.

        Args:
            session: Active MCP ClientSession.
            tool_name: Name of the tool to call.
            arguments: Tool arguments as a dictionary.

        Returns:
            JSON string of the tool result.
        """
        logger.info(f"Calling MCP tool: {tool_name}({arguments})")
        try:
            result = await session.call_tool(tool_name, arguments=arguments)

            # Extract text content from the result
            if result.content:
                # MCP returns content as a list of content blocks
                text_parts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)
                content = "\n".join(text_parts) if text_parts else str(result.content)
            else:
                content = "{}"

            logger.info(f"Tool {tool_name} returned: {content[:200]}...")
            return content

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})

    async def list_openai_tools(self, session: ClientSession) -> list[dict[str, Any]]:
        """Discover MCP tools and convert them to OpenAI tool definitions."""
        if self._openai_tool_cache is not None:
            return self._openai_tool_cache

        result = await session.list_tools()
        tools = getattr(result, "tools", None)
        if tools is None and hasattr(result, "model_dump"):
            tools = result.model_dump().get("tools", [])

        if not tools:
            raise RuntimeError("MCP server returned no tools during discovery.")

        discovered_tools = [self._normalize_tool_definition(tool) for tool in tools]
        self._openai_tool_cache = discovered_tools
        logger.info("Discovered %s MCP tools.", len(discovered_tools))
        return discovered_tools

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
