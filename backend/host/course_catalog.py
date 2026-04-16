"""Course name lookup helpers shared by confirmation and context parsing."""

from __future__ import annotations

import logging
import time

from backend.mcp_server.db.connection import get_connection
from backend.services.supabase import is_supabase_rest_configured, list_courses as list_supabase_courses

logger = logging.getLogger("host.course_catalog")

_CACHE_TTL_SECONDS = 300
_cached_course_names: list[str] = []
_cached_at: float = 0.0


def list_course_names(force_refresh: bool = False) -> list[str]:
    """Return known course names from the active runtime data source.

    In Supabase mode, read from the REST-backed course view. In local test mode,
    fall back to SQLite. If lookup fails, return the last cached result or an
    empty list instead of raising from confirmation/context parsing.
    """

    global _cached_at, _cached_course_names

    now = time.monotonic()
    if not force_refresh and _cached_course_names and now - _cached_at < _CACHE_TTL_SECONDS:
        return list(_cached_course_names)

    loaders = [_load_supabase_course_names] if is_supabase_rest_configured() else []
    loaders.append(_load_sqlite_course_names)

    for loader in loaders:
        try:
            course_names = loader()
        except Exception as exc:
            logger.warning("Course name lookup via %s failed: %s", loader.__name__, exc)
            continue

        if course_names:
            _cached_course_names = course_names
            _cached_at = now
            return list(course_names)

    return list(_cached_course_names)


def _load_supabase_course_names() -> list[str]:
    rows = list_supabase_courses()
    return sorted({str(row["name"]).strip() for row in rows if row.get("name")})


def _load_sqlite_course_names() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT name FROM golf_courses ORDER BY name ASC").fetchall()
    return [str(row["name"]).strip() for row in rows if row["name"]]
