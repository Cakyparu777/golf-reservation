"""JWT authentication utilities."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode
from passlib.context import CryptContext

from backend.mcp_server.db.connection import get_connection
from backend.mcp_server.db.queries import GET_USER_BY_EMAIL, INSERT_USER
from backend.services.supabase import is_supabase_subject

SECRET_KEY = os.getenv("SECRET_KEY", "fairway-elite-dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
_SUPABASE_JWKS_CACHE: dict | None = None


def _supabase_base_url() -> Optional[str]:
    explicit_url = os.getenv("SUPABASE_URL")
    if explicit_url:
        return explicit_url.rstrip("/")

    project_ref = os.getenv("SUPABASE_PROJECT_REF")
    if project_ref:
        return f"https://{project_ref}.supabase.co"

    return None


def _fetch_supabase_jwks() -> dict:
    global _SUPABASE_JWKS_CACHE

    if _SUPABASE_JWKS_CACHE is not None:
        return _SUPABASE_JWKS_CACHE

    base_url = _supabase_base_url()
    if not base_url:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    response = httpx.get(f"{base_url}/auth/v1/.well-known/jwks.json", timeout=5.0)
    response.raise_for_status()
    data = response.json()
    _SUPABASE_JWKS_CACHE = data
    return data


def _verify_supabase_token(token: str) -> dict:
    base_url = _supabase_base_url()
    if not base_url:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.get_unverified_claims(token)
        jwks = _fetch_supabase_jwks()
    except Exception as exc:  # pragma: no cover - defensive parsing guard
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc

    key_data = next((key for key in jwks.get("keys", []) if key.get("kid") == header.get("kid")), None)
    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    public_key = jwk.construct(key_data)
    message, encoded_signature = token.rsplit(".", 1)
    decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))
    if not public_key.verify(message.encode("utf-8"), decoded_signature):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    exp = claims.get("exp")
    if exp is not None and datetime.now(UTC).timestamp() > float(exp):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    expected_issuer = f"{base_url}/auth/v1"
    issuer = str(claims.get("iss") or "")
    if issuer and issuer.rstrip("/") != expected_issuer.rstrip("/"):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return claims


def _resolve_or_create_local_user_id(payload: dict) -> int:
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    metadata = payload.get("user_metadata") or {}
    name = metadata.get("full_name") or metadata.get("name") or str(email).split("@", 1)[0]
    phone = metadata.get("phone") or payload.get("phone")

    with get_connection() as conn:
        conn.execute(
            INSERT_USER,
            {
                "name": name,
                "email": email,
                "phone": phone,
                "home_area": None,
                "travel_mode": None,
                "max_travel_minutes": None,
            },
        )
        user = conn.execute(GET_USER_BY_EMAIL, {"email": email}).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return int(user["id"])


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        try:
            return _verify_supabase_token(token)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
            )


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> int:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    payload = decode_token(credentials.credentials)
    subject = str(payload.get("sub") or "")
    if subject.isdigit():
        return int(subject)
    return _resolve_or_create_local_user_id(payload)


def get_current_auth_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return decode_token(credentials.credentials)


def get_current_access_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return credentials.credentials


def is_supabase_auth_payload(payload: dict) -> bool:
    return is_supabase_subject(payload)
