"""POST /auth/login, POST /auth/logout, GET /auth/me.

Per docs/API.md §2. Logout is best-effort (JWTs are stateless for the demo);
the route exists so the frontend can call it consistently. Both login and
logout write an audit event per docs/AUDIT_LOG.md § Auth.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response

from app.config import Settings
from app.dependencies import CurrentUser, get_audit_writer, get_settings_dep
from app.envelope import Envelope, ok
from app.errors import ErrorCode, HeliosError
from app.models.auth import LoginRequest, LoginResponse, MeResponse
from app.services.audit_writer import AuditWriter
from app.services.auth import AuthError, authenticate, issue_token

router = APIRouter()


@router.post("/login", response_model=Envelope[LoginResponse])
async def login(
    body: LoginRequest,
    settings: Settings = Depends(get_settings_dep),
    audit: AuditWriter = Depends(get_audit_writer),
) -> Envelope[LoginResponse]:
    try:
        user = authenticate(body.email.lower(), body.password, settings)
    except AuthError as exc:
        await audit.write_event(
            type="auth.login_failed",
            actor=body.email.lower(),
            actor_role="developer",
            subject={"kind": "user", "email": body.email.lower()},
            result="failed",
            error=str(exc),
        )
        raise HeliosError(ErrorCode.UNAUTHORIZED, str(exc)) from exc
    token, expires_at = issue_token(user, settings)
    await audit.write_event(
        type="auth.login",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject={"kind": "user", "email": user.email},
        extra={"auth_method": "password"},
    )
    return ok(LoginResponse(token=token, expires_at=expires_at, user=user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: CurrentUser,
    audit: AuditWriter = Depends(get_audit_writer),
) -> Response:
    await audit.write_event(
        type="auth.logout",
        actor=user.email,
        actor_role=user.roles[0].value if user.roles else "developer",
        subject={"kind": "user", "email": user.email},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=Envelope[MeResponse])
async def me(user: CurrentUser) -> Envelope[MeResponse]:
    return ok(MeResponse(user=user))
