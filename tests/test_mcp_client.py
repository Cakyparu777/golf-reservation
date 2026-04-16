"""Tests for persistent MCP client lifecycle."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.host.mcp_client import MCPClient


class FakeStdioContext:
    def __init__(self):
        self.enter_count = 0
        self.exit_count = 0

    async def __aenter__(self):
        self.enter_count += 1
        return "read", "write"

    async def __aexit__(self, exc_type, exc, tb):
        self.exit_count += 1


class FakeSession:
    instances: list["FakeSession"] = []
    list_tools_calls = 0

    def __init__(self, read_stream, write_stream):
        self.read_stream = read_stream
        self.write_stream = write_stream
        self.initialize_calls = 0
        self.call_tool_calls: list[tuple[str, dict]] = []
        self.closed = False
        FakeSession.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.closed = True

    async def initialize(self):
        self.initialize_calls += 1

    async def list_tools(self):
        FakeSession.list_tools_calls += 1
        return SimpleNamespace(
            tools=[
                {
                    "name": "tool_search_tee_times",
                    "description": "Search tee times",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ]
        )

    async def call_tool(self, tool_name, arguments):
        self.call_tool_calls.append((tool_name, arguments))
        return SimpleNamespace(content=[SimpleNamespace(text='{"ok": true}')])


@pytest.mark.asyncio
async def test_mcp_client_reuses_single_persistent_session(monkeypatch):
    stdio_context = FakeStdioContext()
    FakeSession.instances.clear()
    FakeSession.list_tools_calls = 0

    monkeypatch.setattr("backend.host.mcp_client.stdio_client", lambda params: stdio_context)
    monkeypatch.setattr("backend.host.mcp_client.ClientSession", FakeSession)

    client = MCPClient()

    await client.startup()
    tools_first = await client.list_openai_tools()
    tools_second = await client.list_openai_tools()
    result = await client.call_tool("tool_search_tee_times", {"date": "2026-04-17"})
    await client.shutdown()

    assert stdio_context.enter_count == 1
    assert stdio_context.exit_count == 1
    assert len(FakeSession.instances) == 1
    assert FakeSession.instances[0].initialize_calls == 1
    assert FakeSession.list_tools_calls == 1
    assert FakeSession.instances[0].call_tool_calls == [
        ("tool_search_tee_times", {"date": "2026-04-17"})
    ]
    assert tools_first == tools_second
    assert result == '{"ok": true}'


@pytest.mark.asyncio
async def test_clear_tool_cache_forces_tool_rediscovery(monkeypatch):
    stdio_context = FakeStdioContext()
    FakeSession.instances.clear()
    FakeSession.list_tools_calls = 0

    monkeypatch.setattr("backend.host.mcp_client.stdio_client", lambda params: stdio_context)
    monkeypatch.setattr("backend.host.mcp_client.ClientSession", FakeSession)

    client = MCPClient()

    await client.startup()
    await client.list_openai_tools()
    client.clear_tool_cache()
    await client.list_openai_tools()
    await client.shutdown()

    assert FakeSession.list_tools_calls == 2
