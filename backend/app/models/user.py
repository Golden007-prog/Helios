"""User + session models.

Hackathon scope: 4 seeded users (Maya, Anil, Raj, service principal). JWTs are
HS256-signed by ``Settings.jwt_secret``. Production SSO is on the roadmap.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Role(str, Enum):
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    ADMIN = "admin"
    SERVICE = "service"


class UserPreferences(BaseModel):
    default_region_view: str = "int2"
    show_dissent_inline: bool = True
    notify_on_review_decision: bool = True


class UserDoc(BaseModel):
    """Full user document — matches docs/DATA_MODEL.md §8."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(alias="_id")
    rev: str | None = Field(default=None, alias="_rev")
    schema_version: str = "1.0"
    kind: str = "user"
    shop: str = "meridianbank"
    email: EmailStr
    display_name: str
    roles: list[Role]
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: datetime
    last_login_at: datetime | None = None


class AuthenticatedUser(BaseModel):
    """Slim claim-bearing record used in request scope."""

    model_config = ConfigDict(extra="forbid")
    user_id: str
    email: EmailStr
    display_name: str
    roles: list[Role]
    shop: str = "meridianbank"

    def has_role(self, role: Role) -> bool:
        return role in self.roles
