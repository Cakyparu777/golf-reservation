"""Reservations API routes (auth required)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.host.auth import get_current_access_token, get_current_auth_payload, get_current_user_id
from backend.mcp_server.db.connection import get_connection
from backend.mcp_server.db.queries import (
    GET_TEE_TIME_BY_ID,
    INSERT_RESERVATION,
    DECREMENT_AVAILABLE_SLOTS,
    CONFIRM_RESERVATION,
    CANCEL_RESERVATION,
    RESTORE_AVAILABLE_SLOTS,
    INSERT_HISTORY,
    LIST_USER_RESERVATIONS,
    GET_RESERVATION_BY_ID,
    GET_USER_BY_ID,
)
from backend.services.supabase import (
    cancel_reservation as cancel_supabase_reservation,
    get_or_create_user_profile,
    get_my_reservation,
    is_supabase_rest_configured,
    is_supabase_service_role_configured,
    list_my_reservations,
    make_reservation as make_supabase_reservation,
)

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


class CreateReservationRequest(BaseModel):
    tee_time_id: int
    num_players: int = 1


class ReservationOut(BaseModel):
    id: int
    tee_time_id: int
    course_name: str
    tee_datetime: str
    num_players: int
    total_price: float
    status: str
    confirmation_number: Optional[str]
    created_at: Optional[str]


@router.get("", response_model=list[ReservationOut])
def list_reservations(
    user_id: int = Depends(get_current_user_id),
    access_token: str = Depends(get_current_access_token),
):
    if is_supabase_rest_configured():
        return [_row_to_out(r) for r in list_my_reservations(access_token)]

    with get_connection() as conn:
        user = conn.execute(GET_USER_BY_ID, {"user_id": user_id}).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        rows = conn.execute(
            LIST_USER_RESERVATIONS.format(status_filter=""),
            {"email": user["email"]},
        ).fetchall()
    return [_row_to_out(r) for r in rows]


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(
    body: CreateReservationRequest,
    user_id: int = Depends(get_current_user_id),
    payload: dict = Depends(get_current_auth_payload),
    access_token: str = Depends(get_current_access_token),
):
    if is_supabase_rest_configured():
        if not is_supabase_service_role_configured():
            raise HTTPException(status_code=503, detail="Supabase service role key is not configured.")
        profile = get_or_create_user_profile(access_token, payload)
        result = make_supabase_reservation(
            tee_time_id=body.tee_time_id,
            user_name=profile["name"],
            user_email=profile["email"],
            num_players=body.num_players,
            user_phone=profile.get("phone"),
            auth_user_id=profile.get("auth_user_id"),
        )
        if result.get("error"):
            message = str(result["error"])
            status_code = 409 if "available" in message.lower() else 400
            raise HTTPException(status_code=status_code, detail=message)
        reservation = result.get("reservation")
        if not reservation:
            raise HTTPException(status_code=500, detail="Reservation response was missing data.")
        return _row_to_out(reservation)

    with get_connection() as conn:
        tee_time = conn.execute(GET_TEE_TIME_BY_ID, {"tee_time_id": body.tee_time_id}).fetchone()
        if not tee_time:
            raise HTTPException(status_code=404, detail="Tee time not found.")
        if tee_time["available_slots"] < body.num_players:
            raise HTTPException(status_code=409, detail="Not enough available slots.")

        total_price = tee_time["price_per_player"] * body.num_players
        hold_expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()

        conn.execute(
            INSERT_RESERVATION,
            {
                "tee_time_id": body.tee_time_id,
                "user_id": user_id,
                "num_players": body.num_players,
                "total_price": total_price,
                "hold_expires_at": hold_expires,
            },
        )
        reservation_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        updated = conn.execute(
            DECREMENT_AVAILABLE_SLOTS,
            {"tee_time_id": body.tee_time_id, "num_players": body.num_players},
        ).rowcount
        if updated == 0:
            raise HTTPException(status_code=409, detail="Slot no longer available.")

        # Auto-confirm
        confirmation_number = f"FE-{uuid.uuid4().hex[:8].upper()}"
        conn.execute(
            CONFIRM_RESERVATION,
            {"reservation_id": reservation_id, "confirmation_number": confirmation_number},
        )
        conn.execute(
            INSERT_HISTORY,
            {
                "reservation_id": reservation_id,
                "old_status": "PENDING",
                "new_status": "CONFIRMED",
                "reason": "Auto-confirmed on creation",
            },
        )

        row = conn.execute(GET_RESERVATION_BY_ID, {"reservation_id": reservation_id}).fetchone()
    return _row_to_out(row)


@router.delete("/{reservation_id}", status_code=204)
def cancel_reservation(
    reservation_id: int,
    user_id: int = Depends(get_current_user_id),
    access_token: str = Depends(get_current_access_token),
):
    if is_supabase_rest_configured():
        if not is_supabase_service_role_configured():
            raise HTTPException(status_code=503, detail="Supabase service role key is not configured.")
        row = get_my_reservation(access_token, reservation_id)
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found.")
        result = cancel_supabase_reservation(reservation_id=reservation_id, reason="Cancelled by user")
        if result.get("error"):
            raise HTTPException(status_code=409, detail=str(result["error"]))
        return

    with get_connection() as conn:
        row = conn.execute(GET_RESERVATION_BY_ID, {"reservation_id": reservation_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found.")
        if row["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not your reservation.")

        old_status = row["status"]
        updated = conn.execute(
            CANCEL_RESERVATION, {"reservation_id": reservation_id}
        ).rowcount
        if updated == 0:
            raise HTTPException(status_code=409, detail="Cannot cancel reservation in current state.")

        conn.execute(
            RESTORE_AVAILABLE_SLOTS,
            {"tee_time_id": row["tee_time_id"], "num_players": row["num_players"]},
        )
        conn.execute(
            INSERT_HISTORY,
            {
                "reservation_id": reservation_id,
                "old_status": old_status,
                "new_status": "CANCELLED",
                "reason": "Cancelled by user",
            },
        )


def _row_to_out(row) -> ReservationOut:
    return ReservationOut(
        id=row["id"],
        tee_time_id=row["tee_time_id"],
        course_name=row["course_name"],
        tee_datetime=row["tee_datetime"],
        num_players=row["num_players"],
        total_price=float(row["total_price"]),
        status=row["status"],
        confirmation_number=row["confirmation_number"],
        created_at=row["created_at"],
    )
