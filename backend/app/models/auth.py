"""Auth request / response shapes."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import AuthenticatedUser


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    user: AuthenticatedUser


class MeResponse(BaseModel):
    user: AuthenticatedUser
