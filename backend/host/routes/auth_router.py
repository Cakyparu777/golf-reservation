"""Auth routes: register and login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.host.auth import (
    create_access_token,
    get_current_access_token,
    get_current_auth_payload,
    get_current_user_id,
    hash_password,
    is_supabase_auth_payload,
    verify_password,
)
from backend.mcp_server.db.connection import get_connection
from backend.mcp_server.db.queries import (
    GET_USER_BY_EMAIL,
    GET_USER_BY_ID,
    INSERT_USER_AUTH,
    UPDATE_USER_PROFILE,
    INSERT_USER,
)
from backend.services.supabase import get_or_create_user_profile, is_supabase_rest_configured, upsert_user_profile

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: str | None = None
    home_area: str = Field(..., min_length=2, max_length=120)
    travel_mode: str = Field(default="train", pattern="^(train|car|either)$")
    max_travel_minutes: int = Field(default=60, ge=15, le=240)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ProfileUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = None
    home_area: str = Field(..., min_length=2, max_length=120)
    travel_mode: str = Field(default="train", pattern="^(train|car|either)$")
    max_travel_minutes: int = Field(default=60, ge=15, le=240)


def _user_payload(user) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "home_area": user["home_area"],
        "travel_mode": user["travel_mode"],
        "max_travel_minutes": user["max_travel_minutes"],
        "phone": user["phone"],
    }


def _sync_local_user_profile(profile: dict) -> dict:
    with get_connection() as conn:
        conn.execute(
            INSERT_USER,
            {
                "name": profile["name"],
                "email": profile["email"],
                "phone": profile.get("phone"),
                "home_area": profile.get("home_area"),
                "travel_mode": profile.get("travel_mode") or "train",
                "max_travel_minutes": profile.get("max_travel_minutes") or 60,
            },
        )
        user = conn.execute(GET_USER_BY_EMAIL, {"email": profile["email"]}).fetchone()
    return _user_payload(user)


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: RegisterRequest):
    with get_connection() as conn:
        existing = conn.execute(GET_USER_BY_EMAIL, {"email": body.email}).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered.")

        conn.execute(
            INSERT_USER_AUTH,
            {
                "name": body.name,
                "email": body.email,
                "phone": body.phone,
                "home_area": body.home_area,
                "travel_mode": body.travel_mode,
                "max_travel_minutes": body.max_travel_minutes,
                "password_hash": hash_password(body.password),
            },
        )
        user = conn.execute(GET_USER_BY_EMAIL, {"email": body.email}).fetchone()

    token = create_access_token(user["id"], user["email"])
    return AuthResponse(
        access_token=token,
        user=_user_payload(user),
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest):
    with get_connection() as conn:
        user = conn.execute(GET_USER_BY_EMAIL, {"email": body.email}).fetchone()

    if not user or not user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user["id"], user["email"])
    return AuthResponse(
        access_token=token,
        user=_user_payload(user),
    )


@router.get("/me")
def get_me(
    user_id: int = Depends(get_current_user_id),
    payload: dict = Depends(get_current_auth_payload),
    access_token: str = Depends(get_current_access_token),
):
    if is_supabase_auth_payload(payload) and is_supabase_rest_configured():
        profile = get_or_create_user_profile(access_token, payload)
        return _sync_local_user_profile(profile)

    with get_connection() as conn:
        user = conn.execute(GET_USER_BY_ID, {"user_id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return _user_payload(user)


@router.patch("/me")
def update_me(
    body: ProfileUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    payload: dict = Depends(get_current_auth_payload),
    access_token: str = Depends(get_current_access_token),
):
    if is_supabase_auth_payload(payload) and is_supabase_rest_configured():
        profile = upsert_user_profile(
            access_token,
            payload,
            {
                "name": body.name,
                "phone": body.phone,
                "home_area": body.home_area,
                "travel_mode": body.travel_mode,
                "max_travel_minutes": body.max_travel_minutes,
            },
        )
        return _sync_local_user_profile(profile)

    with get_connection() as conn:
        updated = conn.execute(
            UPDATE_USER_PROFILE,
            {
                "user_id": user_id,
                "name": body.name,
                "phone": body.phone,
                "home_area": body.home_area,
                "travel_mode": body.travel_mode,
                "max_travel_minutes": body.max_travel_minutes,
            },
        ).rowcount
        if updated == 0:
            raise HTTPException(status_code=404, detail="User not found.")
        user = conn.execute(GET_USER_BY_ID, {"user_id": user_id}).fetchone()

    return _user_payload(user)
