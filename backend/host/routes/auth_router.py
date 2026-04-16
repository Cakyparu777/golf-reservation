"""Auth routes: register and login."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.host.auth import create_access_token, hash_password, verify_password
from backend.mcp_server.db.connection import get_connection
from backend.mcp_server.db.queries import (
    GET_USER_BY_EMAIL,
    INSERT_USER_AUTH,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


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
                "password_hash": hash_password(body.password),
            },
        )
        user = conn.execute(GET_USER_BY_EMAIL, {"email": body.email}).fetchone()

    token = create_access_token(user["id"], user["email"])
    return AuthResponse(
        access_token=token,
        user={"id": user["id"], "name": user["name"], "email": user["email"]},
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
        user={"id": user["id"], "name": user["name"], "email": user["email"]},
    )
