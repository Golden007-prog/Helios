"""JWT issuance / verification + the seeded MeridianBank users.

Hackathon-scope: a hardcoded set of demo users with the password documented in
docs/API.md §2. Production SSO is a Phase 2 item — see docs/ROADMAP.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import Settings
from app.models.user import AuthenticatedUser, Role


# Demo users — must match docs/API.md §2 and the seed script.
# `_id` strings are stable so tests can reference them.
DEMO_USERS: dict[str, AuthenticatedUser] = {
    "maya@meridianbank.demo": AuthenticatedUser(
        user_id="user:maya@meridianbank.demo:01HXYDEMO00000000000MAYA0",
        email="maya@meridianbank.demo",
        display_name="Maya Patel",
        roles=[Role.DEVELOPER],
    ),
    "anil@meridianbank.demo": AuthenticatedUser(
        user_id="user:anil@meridianbank.demo:01HXYDEMO00000000000ANIL0",
        email="anil@meridianbank.demo",
        display_name="Anil Verma",
        roles=[Role.REVIEWER, Role.DEVELOPER],
    ),
    "raj@meridianbank.demo": AuthenticatedUser(
        user_id="user:raj@meridianbank.demo:01HXYDEMO0000000000000RAJ",
        email="raj@meridianbank.demo",
        display_name="Raj Iyer",
        roles=[Role.ADMIN, Role.REVIEWER, Role.DEVELOPER],
    ),
    "svc@meridianbank.demo": AuthenticatedUser(
        user_id="user:svc@meridianbank.demo:01HXYDEMO00000000000000SVC",
        email="svc@meridianbank.demo",
        display_name="Helios Service",
        roles=[Role.SERVICE],
    ),
}


class AuthError(Exception):
    """Raised by :func:`authenticate` for bad credentials."""


def authenticate(email: str, password: str, settings: Settings) -> AuthenticatedUser:
    """Verify the demo password and return the user record."""
    if password != settings.demo_user_password:
        raise AuthError("Invalid email or password")
    user = DEMO_USERS.get(email.lower())
    if not user:
        raise AuthError("Invalid email or password")
    return user


def issue_token(user: AuthenticatedUser, settings: Settings) -> tuple[str, datetime]:
    """Mint an HS256 JWT carrying the user claims. Returns (token, expires_at)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.jwt_ttl_seconds)
    payload = {
        "sub": user.user_id,
        "email": user.email,
        "name": user.display_name,
        "roles": [r.value for r in user.roles],
        "shop": user.shop,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_token(token: str, settings: Settings) -> AuthenticatedUser:
    """Decode and validate a session JWT into an :class:`AuthenticatedUser`."""
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return AuthenticatedUser(
        user_id=claims["sub"],
        email=claims["email"],
        display_name=claims["name"],
        roles=[Role(r) for r in claims.get("roles", [])],
        shop=claims.get("shop", "meridianbank"),
    )
