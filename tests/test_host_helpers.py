"""Tests for host-side parsing helpers."""

from __future__ import annotations

from backend.host.confirmation import extract_booking_details
from backend.host.session_context import extract_message_context


def test_extract_booking_details_uses_supabase_course_list(monkeypatch):
    monkeypatch.setattr("backend.host.course_catalog._cached_course_names", [])
    monkeypatch.setattr("backend.host.course_catalog._cached_at", 0.0)
    monkeypatch.setattr("backend.host.course_catalog.is_supabase_rest_configured", lambda: True)
    monkeypatch.setattr(
        "backend.host.course_catalog.list_supabase_courses",
        lambda: [{"name": "Tama Hills Golf Course"}, {"name": "Wakasu Golf Links"}],
    )

    details = extract_booking_details("Please book Tama Hills tomorrow at 12:00 for 2 players")

    assert details["course_name"] == "Tama Hills Golf Course"


def test_extract_message_context_does_not_treat_time_as_option_reference():
    context = extract_message_context("book the one at 10am")

    assert context["selected_option_index"] is None
