"""JWT session tokens. Separate from app/security.py (password hashing +
order-status rules) so the "issue/verify a session" concern lives in one
place. Tokens carry a "kind" (user vs customer) so a customer's token can
never be replayed against a staff-only endpoint — only get_current_user
(staff/admin) is actually wired into a route right now."""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

_bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(*, subject: int, kind: str, role: str | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(subject), "kind": kind, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Admin/staff session. Use as a dependency on any admin-only endpoint."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = _decode(credentials.credentials)
    if payload.get("kind") != "user":
        raise HTTPException(status_code=401, detail="This endpoint requires a staff/admin login")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user
