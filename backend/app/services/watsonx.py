"""watsonx.ai client wrapper.

Wraps the IBM Cloud IAM token exchange + the watsonx.ai text generation
endpoint with retry, the banned-model guard, and a streaming helper.

When credentials are missing or ``settings.enable_watsonx`` is False, the
client runs in **stub mode**: ``generate`` returns a deterministic
"watsonx-disabled" payload and ``ping`` reports degraded. This lets the
backend boot in CI / hackathon machines where watsonx hasn't been wired yet.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import Settings
from app.errors import ErrorCode, HeliosError
from app.logging import get_logger

_log = get_logger("helios.watsonx")
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


class WatsonxError(HeliosError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.WATSONX_UPSTREAM, message, details=details)


class _RetryableUpstream(Exception):
    pass


class WatsonxClient:
    """Async watsonx.ai client.

    Stub mode triggers when:

    * ``settings.enable_watsonx`` is False, OR
    * any of (``watsonx_apikey``, ``watsonx_project_id``) is missing.

    Stub responses are clearly labeled so they cannot be mistaken for real
    Granite output in tests or fixtures.
    """

    def __init__(self, settings: Settings, *, http: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._iam_token: str | None = None
        self._iam_expires_at: float = 0.0
        creds_present = bool(settings.watsonx_apikey and settings.watsonx_project_id)
        self._live = settings.enable_watsonx and creds_present

        # Banned-model guard at construction.
        settings.assert_model_allowed(settings.watsonx_default_model)

        if self._live:
            self._http = http or httpx.AsyncClient(
                base_url=str(settings.watsonx_url).rstrip("/"),
                timeout=settings.watsonx_timeout_seconds,
                headers={"Accept": "application/json"},
            )
            self._iam_http = http or httpx.AsyncClient(timeout=settings.watsonx_timeout_seconds)
        else:
            self._http = None
            self._iam_http = None
            _log.info("watsonx.stub_mode", reason="missing_creds_or_disabled")

    @property
    def is_live(self) -> bool:
        return self._live

    async def close(self) -> None:
        for h in (self._http, self._iam_http):
            if h is not None:
                await h.aclose()

    async def ping(self) -> tuple[bool, str | None]:
        if not self._live:
            return False, "stub mode (no credentials)"
        try:
            await self._iam_token_value()
            return True, "iam reachable"
        except Exception as exc:
            return False, str(exc)

    # --- IAM ---------------------------------------------------------------

    async def _iam_token_value(self) -> str:
        """Return a valid IBM Cloud IAM token, refreshing 60 s before expiry."""
        if not self._live:
            raise WatsonxError("watsonx is in stub mode")
        if self._iam_token and time.time() < self._iam_expires_at - 60:
            return self._iam_token
        assert self._iam_http is not None
        resp = await self._iam_http.post(
            IAM_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self._settings.watsonx_apikey or "",
            },
        )
        if resp.status_code >= 400:
            raise WatsonxError(
                "IAM token exchange failed",
                details={"status": resp.status_code, "body": resp.text[:500]},
            )
        data = resp.json()
        self._iam_token = data["access_token"]
        self._iam_expires_at = time.time() + int(data.get("expires_in", 3600))
        assert self._iam_token is not None
        return self._iam_token

    # --- Inference --------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        model_id: str | None = None,
        max_new_tokens: int = 256,
        temperature: float = 0.2,
        stop_sequences: list[str] | None = None,
        purpose: str = "unspecified",
    ) -> dict[str, Any]:
        """One-shot text generation.

        ``purpose`` is included in logs and in the stub-mode response so it's
        always clear which call site produced the output.
        """
        model = model_id or self._settings.watsonx_default_model
        self._settings.assert_model_allowed(model)

        if not self._live:
            return {
                "model_id": model,
                "generated_text": (
                    f"[watsonx-stub: would have generated up to {max_new_tokens} tokens "
                    f"for purpose='{purpose}']"
                ),
                "stop_reason": "stubbed",
                "input_token_count": len(prompt) // 4,
                "generated_token_count": 0,
            }

        body = {
            "model_id": model,
            "input": prompt,
            "project_id": self._settings.watsonx_project_id,
            "parameters": {
                "decoding_method": "greedy" if temperature == 0 else "sample",
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "stop_sequences": stop_sequences or [],
            },
        }
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._settings.watsonx_max_retries),
            wait=wait_exponential_jitter(initial=0.5, max=8.0, jitter=0.5),
            retry=retry_if_exception_type(_RetryableUpstream),
            reraise=True,
        ):
            with attempt:
                resp = await self._call("/ml/v1/text/generation?version=2024-05-31", body)
        # tenacity returns the last yielded value via reraise; capture explicitly.
        return _normalize_generation(resp)

    async def stream(
        self,
        prompt: str,
        *,
        model_id: str | None = None,
        max_new_tokens: int = 256,
        temperature: float = 0.2,
        purpose: str = "unspecified",
    ) -> AsyncIterator[str]:
        """Streaming generation — yields incremental text chunks.

        In stub mode emits the same labeled string in chunks so SSE clients
        can be developed without watsonx access.
        """
        model = model_id or self._settings.watsonx_default_model
        self._settings.assert_model_allowed(model)

        if not self._live:
            stub = (
                f"[watsonx-stub stream: purpose='{purpose}' model='{model}' "
                f"max_new_tokens={max_new_tokens}]"
            )
            for word in stub.split():
                yield word + " "
            return

        # Real streaming endpoint. Errors raise WatsonxError; callers consume
        # via ``async for chunk in client.stream(...)``.
        token = await self._iam_token_value()
        body = {
            "model_id": model,
            "input": prompt,
            "project_id": self._settings.watsonx_project_id,
            "parameters": {
                "decoding_method": "greedy" if temperature == 0 else "sample",
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
            },
        }
        assert self._http is not None
        async with self._http.stream(
            "POST",
            "/ml/v1/text/generation_stream?version=2024-05-31",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        ) as resp:
            if resp.status_code >= 400:
                detail = (await resp.aread()).decode("utf-8", errors="replace")[:500]
                raise WatsonxError(
                    f"watsonx stream returned {resp.status_code}",
                    details={"status": resp.status_code, "body": detail},
                )
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload = line[len("data: ") :].strip()
                if payload == "[DONE]":
                    break
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                for r in parsed.get("results", []):
                    chunk = r.get("generated_text", "")
                    if chunk:
                        yield chunk

    # --- Internals ---------------------------------------------------------

    async def _call(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        token = await self._iam_token_value()
        assert self._http is not None
        resp = await self._http.post(
            path,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
        if resp.status_code >= 500 or resp.status_code == 429:
            raise _RetryableUpstream(f"{resp.status_code} {resp.text[:200]}")
        if resp.status_code >= 400:
            raise WatsonxError(
                f"watsonx returned {resp.status_code}",
                details={"status": resp.status_code, "body": resp.text[:500]},
            )
        return resp.json()


def _normalize_generation(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten the watsonx response shape so callers don't drill into ``results[0]``."""
    results = raw.get("results", [])
    first = results[0] if results else {}
    return {
        "model_id": raw.get("model_id"),
        "generated_text": first.get("generated_text", ""),
        "stop_reason": first.get("stop_reason"),
        "input_token_count": first.get("input_token_count"),
        "generated_token_count": first.get("generated_token_count"),
    }
