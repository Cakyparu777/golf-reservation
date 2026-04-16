"""Tests for the FastAPI chat endpoint."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    """Create a temporary database for API tests."""
    path = tmp_path / "test_api.db"
    os.environ["DATABASE_PATH"] = str(path)
    os.environ["OPENAI_API_KEY"] = "test-key"
    yield
    os.environ.pop("DATABASE_PATH", None)
    os.environ.pop("OPENAI_API_KEY", None)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        from backend.host.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"


class TestChatEndpoint:
    """Tests for the /chat endpoint (with mocked OpenAI)."""

    @pytest.mark.asyncio
    async def test_chat_creates_session(self):
        """A request without session_id should create a new session."""
        from backend.host.app import app

        # Mock the LLM to return a simple response (no tool calls)
        mock_message = MagicMock()
        mock_message.content = "Hello! I'm GolfBot. How can I help you today?"
        mock_message.tool_calls = None
        mock_message.model_dump.return_value = {
            "role": "assistant",
            "content": mock_message.content,
            "tool_calls": None,
        }

        with patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp:

            mock_llm.chat.return_value = mock_message
            mock_llm.parse_tool_calls.return_value = []

            # Mock MCP connect as async context manager
            mock_session = AsyncMock()
            mock_mcp.connect.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_mcp.connect.return_value.__aexit__ = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/chat", json={
                    "message": "Hello!",
                })

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert "session_id" in data
            assert data["session_id"]  # Should not be empty
