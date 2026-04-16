"""Tests for conversation state backends."""

from __future__ import annotations

from types import SimpleNamespace

from backend.host import conversation


def _reset_backend_cache() -> None:
    conversation._backend = None
    conversation._backend_signature = None


class FakeRedisClient:
    def __init__(self):
        self.store: dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        self.store[key] = value

    def get(self, key: str):
        return self.store.get(key)

    def exists(self, key: str) -> int:
        return int(key in self.store)

    def delete(self, *keys: str) -> None:
        for key in keys:
            self.store.pop(key, None)


def test_memory_backend_includes_jpy_prompt(monkeypatch):
    monkeypatch.setenv("CONVERSATION_BACKEND", "memory")
    _reset_backend_cache()

    session_id = conversation.create_session()
    history = conversation.get_history(session_id)

    assert history[0]["role"] == "system"
    assert "Format prices as JPY" in history[0]["content"]


def test_redis_backend_persists_history_and_state(monkeypatch):
    fake_client = FakeRedisClient()

    monkeypatch.setenv("CONVERSATION_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://example.test:6379/0")
    monkeypatch.setattr(
        conversation,
        "redis",
        SimpleNamespace(from_url=lambda *args, **kwargs: fake_client),
    )
    _reset_backend_cache()

    session_id = conversation.create_session()
    conversation.add_message(session_id, "user", "Book something for tomorrow")
    conversation.update_active_context(session_id, {"date": "2026-04-17", "num_players": 2})

    history = conversation.get_history(session_id)
    context = conversation.get_active_context(session_id)

    assert history[-1]["content"] == "Book something for tomorrow"
    assert context["date"] == "2026-04-17"
    assert context["num_players"] == 2
