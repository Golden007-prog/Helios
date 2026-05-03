"""Success response envelope.

Every 2xx body returned by the backend has the shape:

    { "ok": true, "data": <handler-typed payload>, "request_id": "req:..." }

The error counterpart lives in :mod:`app.errors`. Routes return
``Envelope[YourPayload]`` so OpenAPI carries the full schema.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.middleware import current_request_id

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    ok: bool = Field(default=True)
    data: T
    request_id: str = Field(default_factory=current_request_id)


def ok(data: T) -> Envelope[T]:
    """Convenience constructor — ``return ok(payload)``."""
    return Envelope[T](data=data, request_id=current_request_id())
