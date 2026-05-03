"""Runbook request/response shapes — docs/API.md §9."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FixActionType(str, Enum):
    SQL = "sql"
    JCL = "jcl"
    SHELL = "shell"
    MANUAL = "manual"


class FixAction(BaseModel):
    label: str
    type: FixActionType
    language: str | None = None
    code: str | None = None


class AppliesTo(BaseModel):
    abend_code: str
    program: str | None = None
    paragraph: str | None = None


class Runbook(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    title: str
    applies_to: list[AppliesTo]
    body_markdown: str
    fix_actions: list[FixAction] = Field(default_factory=list)
    created_by: str
    created_from_event_id: str | None = None
    success_count: int = 0
    failure_count: int = 0
    last_applied_at: datetime | None = None


class RunbookListResponse(BaseModel):
    runbooks: list[Runbook]
    total: int


class RunbookCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    applies_to: list[AppliesTo] = Field(min_length=1)
    body_markdown: str = Field(min_length=10)
    fix_actions: list[FixAction] = Field(default_factory=list)


class RunbookCreateResponse(BaseModel):
    runbook: Runbook
    audit_event_id: str


class RunbookApplyRequest(BaseModel):
    event_id: str | None = None  # the ABEND event this is being applied to
    notes: str | None = None


class RunbookApplyResponse(BaseModel):
    runbook_id: str
    application_id: str
