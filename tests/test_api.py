"""Tests for the FastAPI chat endpoint."""

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import JWTError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_CHAT_USER_COUNTER = 0


async def auth_headers(client: AsyncClient) -> dict[str, str]:
    global _CHAT_USER_COUNTER
    _CHAT_USER_COUNTER += 1
    response = await client.post(
        "/auth/register",
        json={
            "name": f"Chat User {_CHAT_USER_COUNTER}",
            "email": f"chat-user-{_CHAT_USER_COUNTER}@example.com",
            "password": "secret123",
            "home_area": "Adachi-ku",
            "travel_mode": "train",
            "max_travel_minutes": 60,
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    """Create a temporary database for API tests."""
    path = tmp_path / "test_api.db"
    os.environ.pop("SUPABASE_PROJECT_REF", None)
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_PUBLISHABLE_KEY", None)
    os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
    os.environ.pop("NEXT_PUBLIC_SUPABASE_URL", None)
    os.environ.pop("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", None)
    os.environ["DATABASE_PATH"] = str(path)
    os.environ["OPENAI_API_KEY"] = "test-key"
    from backend.db.seed_data import seed_database

    seed_database(path)
    yield
    os.environ.pop("DATABASE_PATH", None)
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("SUPABASE_PROJECT_REF", None)
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_PUBLISHABLE_KEY", None)
    os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
    os.environ.pop("NEXT_PUBLIC_SUPABASE_URL", None)
    os.environ.pop("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", None)


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


class TestAuthEndpoint:
    """Tests for auth endpoints."""

    @pytest.mark.asyncio
    async def test_register_stores_profile_preferences(self):
        from backend.host.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/auth/register",
                json={
                    "name": "Tuguldur",
                    "email": "tuguldur@example.com",
                    "password": "secret123",
                    "home_area": "Adachi-ku",
                    "travel_mode": "train",
                    "max_travel_minutes": 60,
                },
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["user"]["home_area"] == "Adachi-ku"
        assert payload["user"]["travel_mode"] == "train"
        assert payload["user"]["max_travel_minutes"] == 60

    @pytest.mark.asyncio
    async def test_profile_update_endpoint(self):
        from backend.host.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            register = await client.post(
                "/auth/register",
                json={
                    "name": "Tuguldur",
                    "email": "profile@example.com",
                    "password": "secret123",
                    "home_area": "Adachi-ku",
                    "travel_mode": "train",
                    "max_travel_minutes": 60,
                },
            )
            token = register.json()["access_token"]

            update = await client.patch(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": "Tuguldur Ganbaatar",
                    "phone": "070-0000-0000",
                    "home_area": "Kita-Senju",
                    "travel_mode": "either",
                    "max_travel_minutes": 90,
                },
            )
            profile = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert update.status_code == 200
        assert update.json()["home_area"] == "Kita-Senju"
        assert update.json()["travel_mode"] == "either"
        assert update.json()["max_travel_minutes"] == 90
        assert profile.status_code == 200
        assert profile.json()["phone"] == "070-0000-0000"

    @pytest.mark.asyncio
    async def test_auth_me_returns_local_user_profile(self):
        from backend.host.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            register = await client.post(
                "/auth/register",
                json={
                    "name": "Local User",
                    "email": "local-user@example.com",
                    "password": "secret123",
                    "home_area": "Adachi-ku",
                    "travel_mode": "train",
                    "max_travel_minutes": 60,
                },
            )
            token = register.json()["access_token"]
            response = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["email"] == "local-user@example.com"
        assert payload["name"] == "Local User"

    @pytest.mark.asyncio
    async def test_auth_me_accepts_supabase_jwt_and_creates_local_user(self, monkeypatch):
        from backend.host.app import app

        monkeypatch.setenv("SUPABASE_PROJECT_REF", "dvtktsuzxqssksbnvjnn")
        monkeypatch.setattr("backend.host.auth._SUPABASE_JWKS_CACHE", None)

        transport = ASGITransport(app=app)
        with patch("backend.host.auth.jwt.decode", side_effect=JWTError("invalid local token")), \
             patch(
                 "backend.host.auth._verify_supabase_token",
                 return_value={
                     "sub": "1c2d3e4f-5555-6666-7777-888899990000",
                     "email": "supabase-user@example.com",
                     "user_metadata": {"full_name": "Supabase User"},
                 },
             ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/auth/me",
                    headers={"Authorization": "Bearer supabase.jwt.token"},
                )

        assert response.status_code == 200
        payload = response.json()
        assert payload["email"] == "supabase-user@example.com"
        assert payload["name"] == "Supabase User"

    @pytest.mark.asyncio
    async def test_auth_me_uses_supabase_profile_service_when_configured(self, monkeypatch):
        from backend.host.app import app

        monkeypatch.setenv("SUPABASE_URL", "https://dvtktsuzxqssksbnvjnn.supabase.co")
        monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")

        transport = ASGITransport(app=app)
        with patch("backend.host.auth.jwt.decode", side_effect=JWTError("invalid local token")), \
             patch(
                 "backend.host.auth._verify_supabase_token",
                 return_value={
                     "sub": "11111111-2222-3333-4444-555555555555",
                     "email": "profiled@example.com",
                     "user_metadata": {"full_name": "Profiled User"},
                 },
             ), \
             patch(
                 "backend.host.routes.auth_router.get_or_create_user_profile",
                 return_value={
                     "email": "profiled@example.com",
                     "name": "Profiled User",
                     "phone": None,
                     "home_area": "Adachi-ku",
                     "travel_mode": "train",
                     "max_travel_minutes": 60,
                 },
             ) as mock_profile:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/auth/me",
                    headers={"Authorization": "Bearer supabase.jwt.token"},
                )

        assert response.status_code == 200
        assert response.json()["home_area"] == "Adachi-ku"
        mock_profile.assert_called_once()


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
            mock_mcp.list_openai_tools = AsyncMock(return_value=[])

            # Mock MCP connect as async context manager
            mock_session = AsyncMock()
            mock_mcp.connect.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_mcp.connect.return_value.__aexit__ = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                response = await client.post("/chat", json={
                    "message": "Hello!",
                }, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert "session_id" in data
            assert data["session_id"]  # Should not be empty

    @pytest.mark.asyncio
    async def test_chat_requires_authentication(self):
        from backend.host.app import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "Hello!"})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_uses_saved_profile_context_when_request_omits_it(self):
        from backend.host.app import app

        with patch("backend.host.app.find_nearest_courses") as mock_nearest, \
             patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp:

            mock_nearest.return_value = {
                "user_area": "Adachi-ku",
                "travel_mode": "train",
                "nearest_courses": [
                    {
                        "id": 1,
                        "name": "Wakasu Golf Links",
                        "location": "Koto City, Tokyo",
                        "travel_minutes": 29,
                    }
                ],
            }

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                response = await client.post(
                    "/chat",
                    json={"message": "where is the nearest golf course to me"},
                    headers=headers,
                )

            assert response.status_code == 200
            mock_nearest.assert_called_once()
            assert mock_nearest.call_args.kwargs["user_area"] == "Adachi-ku"
            mock_llm.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_chat_skips_profile_lookup_when_request_already_has_profile(self):
        from backend.host.app import app

        mock_message = MagicMock()
        mock_message.content = "Using provided profile details."
        mock_message.tool_calls = None
        mock_message.model_dump.return_value = {
            "role": "assistant",
            "content": mock_message.content,
            "tool_calls": None,
        }

        with patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp, \
             patch("backend.host.app._load_authenticated_profile_context") as mock_profile_loader:

            mock_llm.chat.return_value = mock_message
            mock_llm.parse_tool_calls.return_value = []
            mock_mcp.list_openai_tools = AsyncMock(return_value=[])

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                response = await client.post(
                    "/chat",
                    json={
                        "message": "where is the nearest golf course to me",
                        "user_name": "Chat User",
                        "home_area": "Adachi-ku",
                        "travel_mode": "train",
                        "max_travel_minutes": 60,
                    },
                    headers=headers,
                )

            assert response.status_code == 200
            mock_profile_loader.assert_not_called()

    @pytest.mark.asyncio
    async def test_chat_returns_nearest_course_from_saved_home_area_without_llm(self):
        from backend.host.app import app

        with patch("backend.host.app.find_nearest_courses") as mock_nearest, \
             patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp:

            mock_nearest.return_value = {
                "user_area": "Adachi-ku",
                "travel_mode": "train",
                "nearest_courses": [
                    {
                        "id": 1,
                        "name": "Wakasu Golf Links",
                        "location": "Koto City, Tokyo",
                        "travel_minutes": 29,
                    },
                    {
                        "id": 2,
                        "name": "Tokyo Kokusai Golf Club",
                        "location": "Machida, Tokyo",
                        "travel_minutes": 55,
                    },
                ],
            }

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                response = await client.post(
                    "/chat",
                    json={"message": "what's the nearest golf course to me"},
                    headers=headers,
                )

            assert response.status_code == 200
            payload = response.json()
            assert "Wakasu Golf Links" in payload["reply"]
            assert "Adachi-ku" in payload["reply"]
            assert payload["tool_calls_made"] == []
            mock_llm.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_chat_requests_confirmation_before_booking(self):
        from backend.host.app import app

        with patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp, \
             patch("backend.host.app.get_weather_forecast") as mock_weather:

            mock_weather.return_value = {
                "assessment": "good",
                "message": "Conditions look good for golf: partly cloudy, 20C, 10% rain chance, 8 km/h wind.",
            }
            mock_mcp.list_openai_tools = AsyncMock(return_value=[])
            mock_session = AsyncMock()
            mock_mcp.connect.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_mcp.connect.return_value.__aexit__ = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                response = await client.post(
                    "/chat",
                    json={"message": "Please book Tama Hills Golf Course on 04/16/2026 at 12:00 for 2 players."},
                    headers=headers,
                )

            assert response.status_code == 200
            data = response.json()
            assert "Can you confirm these details?" in data["reply"]
            assert "Date: 2026-04-16" in data["reply"]
            assert "Time: 12:00" in data["reply"]
            assert "Golf course: Tama Hills Golf Course" in data["reply"]
            assert "Players: 2" in data["reply"]
            assert data["tool_calls_made"] == []
            mock_llm.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_chat_proceeds_after_confirmation(self):
        from backend.host.app import app

        mock_message = MagicMock()
        mock_message.content = "Confirmed - I'll look for tee times now."
        mock_message.tool_calls = None
        mock_message.model_dump.return_value = {
            "role": "assistant",
            "content": mock_message.content,
            "tool_calls": None,
        }

        with patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp, \
             patch("backend.host.app.get_weather_forecast") as mock_weather:

            mock_llm.chat.return_value = mock_message
            mock_llm.parse_tool_calls.return_value = []
            mock_mcp.list_openai_tools = AsyncMock(return_value=[])
            mock_weather.return_value = {
                "assessment": "good",
                "message": "Conditions look good for golf: partly cloudy, 20C, 10% rain chance, 8 km/h wind.",
            }

            mock_session = AsyncMock()
            mock_mcp.connect.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_mcp.connect.return_value.__aexit__ = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                first = await client.post(
                    "/chat",
                    json={"message": "Please book Tama Hills Golf Course on 04/16/2026 at 12:00 for 2 players."},
                    headers=headers,
                )
                session_id = first.json()["session_id"]
                second = await client.post(
                    "/chat",
                    json={"message": "yes", "session_id": session_id},
                    headers=headers,
                )

            assert second.status_code == 200
            assert second.json()["reply"] == "Confirmed - I'll look for tee times now."
            mock_llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_augments_pending_reservation_with_weather_recheck(self):
        from backend.host.app import app

        tool_call_message = MagicMock()
        tool_call_message.content = None
        tool_call_message.tool_calls = [MagicMock()]
        tool_call_message.model_dump.return_value = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "tool_make_reservation", "arguments": "{}"},
                }
            ],
        }

        final_message = MagicMock()
        final_message.content = "Please confirm your reservation."
        final_message.tool_calls = None
        final_message.model_dump.return_value = {
            "role": "assistant",
            "content": final_message.content,
            "tool_calls": None,
        }

        with patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp, \
             patch("backend.host.app.get_weather_forecast") as mock_weather:

            mock_llm.chat.side_effect = [tool_call_message, final_message]
            mock_llm.parse_tool_calls.side_effect = [
                [{"id": "call_1", "name": "tool_make_reservation", "arguments": {"tee_time_id": 123, "num_players": 2}}],
                [],
            ]
            mock_weather.return_value = {
                "assessment": "mixed",
                "message": "Conditions are playable but not ideal: moderate rain, 18C, 40% rain chance, 18 km/h wind.",
            }
            mock_mcp.list_openai_tools = AsyncMock(return_value=[])

            mock_session = AsyncMock()
            mock_mcp.connect.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_mcp.connect.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_mcp.call_tool = AsyncMock(return_value=(
                '{"reservation": {"id": 44, "course_name": "Tama Hills Golf Course", '
                '"tee_datetime": "2026-04-16T12:00:00"}, '
                '"message": "Reservation created! Please confirm within 10 minutes."}'
            ))

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                response = await client.post(
                    "/chat",
                    json={"message": "Please continue with the reservation."},
                    headers=headers,
                )

            assert response.status_code == 200
            assert response.json()["reply"] == "Please confirm your reservation."
            second_chat_messages = mock_llm.chat.call_args_list[1].args[0]
            tool_messages = [message for message in second_chat_messages if message.get("role") == "tool"]
            assert tool_messages
            assert "Weather re-check:" in tool_messages[-1]["content"]
            assert '"weather_check":' in tool_messages[-1]["content"]

    @pytest.mark.asyncio
    async def test_chat_returns_502_for_malformed_tool_call(self):
        from backend.host.app import app
        from backend.host.llm import ToolCallParseError

        malformed_message = MagicMock()
        malformed_message.tool_calls = [MagicMock()]

        with patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp:

            mock_llm.chat.return_value = malformed_message
            mock_llm.parse_tool_calls.side_effect = ToolCallParseError("bad tool payload")
            mock_mcp.list_openai_tools = AsyncMock(return_value=[{"type": "function", "function": {"name": "tool_search_tee_times", "description": "", "parameters": {"type": "object", "properties": {}}}}])

            mock_session = AsyncMock()
            mock_mcp.connect.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_mcp.connect.return_value.__aexit__ = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                response = await client.post("/chat", json={"message": "book a tee time"}, headers=headers)

        assert response.status_code == 502
        assert response.json()["detail"] == "The language model returned an invalid tool call."

    @pytest.mark.asyncio
    async def test_chat_reuses_active_course_for_weather_follow_up(self, monkeypatch):
        from backend.host.app import app

        fixed_now = datetime(2026, 4, 16, 17, 0, 0)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        monkeypatch.setattr("backend.host.session_context.datetime", FixedDateTime)

        first = MagicMock()
        first.content = "The nearest full course to Adachi-ku is Wakasu Golf Links in Koto City."
        first.tool_calls = None
        first.model_dump.return_value = {"role": "assistant", "content": first.content, "tool_calls": None}

        third = MagicMock()
        third.content = "For Wakasu Golf Links tomorrow around 12:00, conditions look good for golf."
        third.tool_calls = None
        third.model_dump.return_value = {"role": "assistant", "content": third.content, "tool_calls": None}

        with patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp:

            mock_llm.chat.side_effect = [first, third]
            mock_llm.parse_tool_calls.side_effect = [[], []]
            mock_mcp.list_openai_tools = AsyncMock(return_value=[])

            mock_session = AsyncMock()
            mock_mcp.connect.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_mcp.connect.return_value.__aexit__ = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                response_one = await client.post("/chat", json={"message": "nearest to adachi ku"}, headers=headers)
                session_id = response_one.json()["session_id"]
                await client.post("/chat", json={"message": "tomorrow 12:00 3-4 players", "session_id": session_id}, headers=headers)
                response_three = await client.post(
                    "/chat",
                    json={"message": "how will be the weather that day", "session_id": session_id},
                    headers=headers,
                )

            assert response_three.status_code == 200
            assert response_three.json()["reply"] == third.content
            assert len(mock_llm.chat.call_args_list) == 2
            third_call_history = mock_llm.chat.call_args_list[1].args[0]
            context_notes = [message["content"] for message in third_call_history if message.get("role") == "system"]
            assert any("Active course: Wakasu Golf Links" in note for note in context_notes)
            assert any("Active date: 2026-04-17" in note for note in context_notes)
            assert any("Active time: 12:00" in note for note in context_notes)
            assert any("Party size range: 3-4 players; use 4 players" in note for note in context_notes)

    @pytest.mark.asyncio
    async def test_chat_resolves_option_reference_from_last_presented_slots(self, monkeypatch):
        from backend.host.app import app

        fixed_now = datetime(2026, 4, 16, 17, 0, 0)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        monkeypatch.setattr("backend.host.session_context.datetime", FixedDateTime)

        first = MagicMock()
        first.content = (
            "Here are tee times at Wakasu Golf Links for tomorrow:\n"
            "1. **12:00 PM** - JPY 12,300 per player\n"
            "2. **12:30 PM** - JPY 12,300 per player\n"
            "3. **1:00 PM** - JPY 12,300 per player"
        )
        first.tool_calls = None
        first.model_dump.return_value = {"role": "assistant", "content": first.content, "tool_calls": None}

        with patch("backend.host.app.llm_client") as mock_llm, \
             patch("backend.host.app.mcp_client") as mock_mcp:

            mock_llm.chat.side_effect = [first]
            mock_llm.parse_tool_calls.side_effect = [[]]
            mock_mcp.list_openai_tools = AsyncMock(return_value=[])

            mock_session = AsyncMock()
            mock_mcp.connect.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_mcp.connect.return_value.__aexit__ = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await auth_headers(client)
                response_one = await client.post("/chat", json={"message": "tomorrow 12:00 4 players"}, headers=headers)
                session_id = response_one.json()["session_id"]
                response_two = await client.post(
                    "/chat",
                    json={"message": "book the second one", "session_id": session_id},
                    headers=headers,
                )

            assert response_two.status_code == 200
            assert "Can you confirm these details?" in response_two.json()["reply"]
            assert "Golf course: Wakasu Golf Links" in response_two.json()["reply"]
            assert "Time: 12:30" in response_two.json()["reply"]
            mock_llm.chat.assert_called_once()


class TestWeatherEndpoint:
    @pytest.mark.asyncio
    async def test_weather_endpoint(self):
        from backend.host.app import app

        with patch("backend.host.routes.weather_router.get_weather_forecast") as mock_weather:
            mock_weather.return_value = {
                "course_name": "Wakasu Golf Links",
                "assessment": "good",
                "message": "Conditions look good for golf: clear sky, 21C, 5% rain chance, 10 km/h wind.",
            }

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/weather",
                    params={"course_name": "Wakasu Golf Links", "date": "2026-04-16", "time": "12:00"},
                )

            assert response.status_code == 200
            assert response.json()["assessment"] == "good"


class TestRecommendationEndpoint:
    @pytest.mark.asyncio
    async def test_recommendation_endpoint(self):
        from backend.host.app import app

        with patch("backend.host.routes.recommendations_router.recommend_tee_times") as mock_recommend:
            mock_recommend.return_value = {
                "recommended_tee_times": [
                    {
                        "tee_time": {
                            "id": 1,
                            "course_id": 1,
                            "tee_datetime": "2026-04-17T08:00:00",
                            "available_slots": 4,
                            "price_per_player": 99.0,
                            "course_name": "Wakasu Golf Links",
                            "course_location": "Koto City, Tokyo",
                        },
                        "weather_assessment": "good",
                        "weather_message": "Conditions look good for golf.",
                        "recommendation_reason": "Best pick for solid weather and overall value.",
                        "score": 128.0,
                    }
                ],
                "message": "Found 1 recommended tee times based on weather, value, and availability.",
            }

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/recommendations",
                    params={"date": "2026-04-17", "num_players": 1, "preferred_time": "morning", "max_results": 3},
                )

            assert response.status_code == 200
            payload = response.json()
            assert payload["recommended_tee_times"][0]["weather_assessment"] == "good"
            assert payload["recommended_tee_times"][0]["tee_time"]["course_name"] == "Wakasu Golf Links"
