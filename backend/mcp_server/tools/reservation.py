"""Reservation management tools.

MCP tools for creating, confirming, and cancelling reservations
with two-phase booking (PENDING → CONFIRMED).
"""

from __future__ import annotations

import os
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.services.supabase import (
    cancel_reservation as cancel_supabase_reservation,
    confirm_reservation as confirm_supabase_reservation,
    is_supabase_service_role_configured,
    make_reservation as make_supabase_reservation,
)

from ..db.connection import get_connection
from ..db.models import Reservation, ReservationResult, ReservationStatus
from ..db import queries


def _format_jpy(amount: float) -> str:
    return f"JPY {amount:,.0f}"


def _generate_confirmation_number() -> str:
    """Generate a human-readable confirmation number like GR-20260418-A3X9."""
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"GR-{date_part}-{random_part}"


def _expire_stale_holds(conn) -> None:
    """Expire any PENDING reservations whose hold has lapsed."""
    # Find reservations to expire so we can restore slots
    stale = conn.execute(
        """
        SELECT id, tee_time_id, num_players
        FROM reservations
        WHERE status = 'PENDING' AND hold_expires_at < datetime('now')
        """
    ).fetchall()

    for row in stale:
        conn.execute(queries.RESTORE_AVAILABLE_SLOTS, {
            "num_players": row["num_players"],
            "tee_time_id": row["tee_time_id"],
        })
        conn.execute(queries.INSERT_HISTORY, {
            "reservation_id": row["id"],
            "old_status": "PENDING",
            "new_status": "EXPIRED",
            "reason": "Hold expired automatically",
        })

    conn.execute(queries.EXPIRE_STALE_HOLDS)


def make_reservation(
    tee_time_id: int,
    user_name: str,
    user_email: str,
    num_players: int,
    user_phone: Optional[str] = None,
) -> dict:
    """Create a pending reservation.

    The reservation is held for 10 minutes. The user must explicitly
    confirm it before the hold expires.

    Args:
        tee_time_id: The tee time slot to book.
        user_name: Name for the booking.
        user_email: Email for confirmation.
        num_players: Number of players (1-4).
        user_phone: Optional phone number.

    Returns:
        Dictionary with the reservation details and status message.
    """
    if os.getenv("SUPABASE_URL") and not is_supabase_service_role_configured():
        return {"error": "Supabase service role key is not configured."}

    if is_supabase_service_role_configured():
        return make_supabase_reservation(
            tee_time_id=tee_time_id,
            user_name=user_name,
            user_email=user_email,
            num_players=num_players,
            user_phone=user_phone,
        )

    if num_players < 1 or num_players > 4:
        return {"error": "Number of players must be between 1 and 4."}

    with get_connection() as conn:
        # Expire any stale holds first
        _expire_stale_holds(conn)

        # Verify the tee time exists and has enough slots
        tee_time = conn.execute(
            queries.GET_TEE_TIME_BY_ID, {"tee_time_id": tee_time_id}
        ).fetchone()

        if not tee_time:
            return {"error": f"Tee time {tee_time_id} not found."}

        if not tee_time["is_active"]:
            return {"error": "This tee time is no longer available."}

        if tee_time["available_slots"] < num_players:
            return {
                "error": f"Only {tee_time['available_slots']} slots available, "
                         f"but {num_players} requested.",
            }

        # Upsert user
        conn.execute(queries.INSERT_USER, {
            "name": user_name,
            "email": user_email,
            "phone": user_phone,
            "home_area": None,
            "travel_mode": None,
            "max_travel_minutes": None,
        })
        user = conn.execute(queries.GET_USER_BY_EMAIL, {"email": user_email}).fetchone()

        # Calculate total price
        total_price = round(tee_time["price_per_player"] * num_players, 2)
        hold_expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

        # Decrement available slots
        result = conn.execute(queries.DECREMENT_AVAILABLE_SLOTS, {
            "tee_time_id": tee_time_id,
            "num_players": num_players,
        })
        if result.rowcount == 0:
            return {"error": "Failed to reserve slots. The tee time may have been booked by someone else."}

        # Create reservation
        cursor = conn.execute(queries.INSERT_RESERVATION, {
            "tee_time_id": tee_time_id,
            "user_id": user["id"],
            "num_players": num_players,
            "total_price": total_price,
            "hold_expires_at": hold_expires,
        })
        reservation_id = cursor.lastrowid

        # Log history
        conn.execute(queries.INSERT_HISTORY, {
            "reservation_id": reservation_id,
            "old_status": None,
            "new_status": "PENDING",
            "reason": "Reservation created",
        })

        # Fetch the full reservation with joined fields
        reservation_row = conn.execute(
            queries.GET_RESERVATION_BY_ID, {"reservation_id": reservation_id}
        ).fetchone()

    reservation = Reservation(**dict(reservation_row))
    return ReservationResult(
        reservation=reservation,
        message=f"Reservation created! Please confirm within 10 minutes. "
                f"Booking: {reservation.course_name} on {reservation.tee_datetime} "
                f"for {num_players} player(s). Total: {_format_jpy(total_price)}.",
    ).model_dump()


def confirm_reservation(reservation_id: int) -> dict:
    """Confirm a pending reservation.

    Args:
        reservation_id: The reservation to confirm.

    Returns:
        Dictionary with updated reservation and confirmation number.
    """
    if os.getenv("SUPABASE_URL") and not is_supabase_service_role_configured():
        return {"error": "Supabase service role key is not configured."}

    if is_supabase_service_role_configured():
        return confirm_supabase_reservation(reservation_id)

    with get_connection() as conn:
        # Expire stale holds
        _expire_stale_holds(conn)

        # Fetch current reservation
        row = conn.execute(
            queries.GET_RESERVATION_BY_ID, {"reservation_id": reservation_id}
        ).fetchone()

        if not row:
            return {"error": f"Reservation {reservation_id} not found."}

        reservation = Reservation(**dict(row))

        if reservation.status == ReservationStatus.CONFIRMED:
            return {"error": "This reservation is already confirmed.",
                    "reservation": reservation.model_dump()}

        if reservation.status != ReservationStatus.PENDING:
            return {"error": f"Cannot confirm a reservation with status '{reservation.status.value}'."}

        # Check if hold has expired
        if reservation.hold_expires_at:
            hold_dt = datetime.fromisoformat(reservation.hold_expires_at)
            if hold_dt < datetime.now(timezone.utc):
                return {"error": "The hold on this reservation has expired. Please create a new booking."}

        # Confirm it
        confirmation_number = _generate_confirmation_number()
        conn.execute(queries.CONFIRM_RESERVATION, {
            "reservation_id": reservation_id,
            "confirmation_number": confirmation_number,
        })

        # Log history
        conn.execute(queries.INSERT_HISTORY, {
            "reservation_id": reservation_id,
            "old_status": "PENDING",
            "new_status": "CONFIRMED",
            "reason": "User confirmed",
        })

        # Fetch updated
        updated_row = conn.execute(
            queries.GET_RESERVATION_BY_ID, {"reservation_id": reservation_id}
        ).fetchone()

    updated = Reservation(**dict(updated_row))
    return ReservationResult(
        reservation=updated,
        message=f"Reservation confirmed! Your confirmation number is {confirmation_number}. "
                f"Enjoy your round at {updated.course_name}!",
    ).model_dump()


def cancel_reservation(
    reservation_id: int,
    reason: Optional[str] = None,
) -> dict:
    """Cancel an existing reservation.

    Args:
        reservation_id: The reservation to cancel.
        reason: Optional cancellation reason.

    Returns:
        Dictionary with cancellation confirmation.
    """
    if os.getenv("SUPABASE_URL") and not is_supabase_service_role_configured():
        return {"error": "Supabase service role key is not configured."}

    if is_supabase_service_role_configured():
        return cancel_supabase_reservation(reservation_id, reason)

    with get_connection() as conn:
        # Fetch current reservation
        row = conn.execute(
            queries.GET_RESERVATION_BY_ID, {"reservation_id": reservation_id}
        ).fetchone()

        if not row:
            return {"error": f"Reservation {reservation_id} not found."}

        reservation = Reservation(**dict(row))

        if reservation.status == ReservationStatus.CANCELLED:
            return {"error": "This reservation is already cancelled."}

        if reservation.status == ReservationStatus.EXPIRED:
            return {"error": "This reservation has expired and cannot be cancelled."}

        old_status = reservation.status.value

        # Cancel the reservation
        result = conn.execute(queries.CANCEL_RESERVATION, {
            "reservation_id": reservation_id,
        })

        if result.rowcount == 0:
            return {"error": "Failed to cancel reservation."}

        # Restore available slots
        conn.execute(queries.RESTORE_AVAILABLE_SLOTS, {
            "num_players": reservation.num_players,
            "tee_time_id": reservation.tee_time_id,
        })

        # Log history
        conn.execute(queries.INSERT_HISTORY, {
            "reservation_id": reservation_id,
            "old_status": old_status,
            "new_status": "CANCELLED",
            "reason": reason or "User cancelled",
        })

        # Fetch updated
        updated_row = conn.execute(
            queries.GET_RESERVATION_BY_ID, {"reservation_id": reservation_id}
        ).fetchone()

    updated = Reservation(**dict(updated_row))
    return ReservationResult(
        reservation=updated,
        message=f"Reservation cancelled successfully. "
                f"The tee time slot has been released.",
    ).model_dump()
