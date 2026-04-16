"""User-related tools.

MCP tools for listing a user's reservations.
"""

from __future__ import annotations

from typing import Optional

from ..db.connection import get_connection
from ..db.models import Reservation
from ..db import queries


def list_user_reservations(
    user_email: str,
    status_filter: Optional[str] = None,
) -> dict:
    """List all reservations for a user.

    Args:
        user_email: The user's email address.
        status_filter: Optional filter: PENDING, CONFIRMED, CANCELLED, EXPIRED, or ALL.
            Defaults to ALL if not specified.

    Returns:
        Dictionary with a list of reservations and count.
    """
    status = (status_filter or "ALL").upper()

    # Build query
    if status == "ALL":
        filter_clause = ""
        params: dict = {"email": user_email}
    else:
        filter_clause = queries.LIST_USER_RESERVATIONS_STATUS_FILTER
        params = {"email": user_email, "status": status}

    query = queries.LIST_USER_RESERVATIONS.format(status_filter=filter_clause)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    reservations = [Reservation(**dict(row)) for row in rows]

    if not reservations:
        return {
            "reservations": [],
            "total": 0,
            "message": f"No reservations found for {user_email}.",
        }

    return {
        "reservations": [r.model_dump() for r in reservations],
        "total": len(reservations),
        "message": f"Found {len(reservations)} reservation(s) for {user_email}.",
    }
