"""watsonx MCP server.

Wraps Granite Code calls with shop-aware prompt templates so Bob can iterate
on prompt tweaks without leaving the IDE.

The set of templates lives in docs/CORPUS.md and the per-shop dialect
adaptation lives in docs/LEARNING_LOOP.md. Each tool below has a typed input
schema and implements the watsonx.ai text generation API.

Banned-model guard: tool handlers reject any model in the banned list
from shared/constants/banned_watsonx_models.json before issuing any watsonx call.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from _shared import ToolError, ToolRegistry, run_cli

WATSONX_URL = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_PROJECT_ID = os.environ.get("WATSONX_PROJECT_ID", "")
WATSONX_APIKEY = os.environ.get("WATSONX_APIKEY", "")
WATSONX_DEFAULT_MODEL = os.environ.get("WATSONX_DEFAULT_MODEL", "ibm/granite-code-8b-instruct")
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
TIMEOUT_S = float(os.environ.get("WATSONX_TIMEOUT_SECONDS", "30"))

# Load banned models from shared constants
REPO_ROOT = Path(__file__).resolve().parents[2]
BANNED_MODELS_PATH = REPO_ROOT / "shared" / "constants" / "banned_watsonx_models.json"
BANNED_MODELS: frozenset[str] = frozenset()

if BANNED_MODELS_PATH.exists():
    with open(BANNED_MODELS_PATH) as f:
        data = json.load(f)
        BANNED_MODELS = frozenset(data.get("banned", []))

registry = ToolRegistry(
    server_name="helios-watsonx",
    description="Granite Code with shop-aware prompt templates.",
)

# IAM token cache
_iam_token: str | None = None
_iam_expires_at: float = 0.0


def _assert_model_allowed(model_id: str) -> None:
    """Raise ToolError if model is banned."""
    if model_id in BANNED_MODELS:
        raise ToolError(
            f"Model {model_id!r} is banned per shared/constants/banned_watsonx_models.json",
            code="BANNED_MODEL",
        )


async def _get_iam_token() -> str:
    """Get or refresh IBM Cloud IAM token."""
    global _iam_token, _iam_expires_at

    if not WATSONX_APIKEY:
        raise ToolError("WATSONX_APIKEY is not set", code="CONFIG_MISSING")

    # Return cached token if still valid (with 60s buffer)
    if _iam_token and time.time() < _iam_expires_at - 60:
        return _iam_token

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            IAM_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": WATSONX_APIKEY,
            },
        )
        if resp.status_code >= 400:
            raise ToolError(
                f"IAM token exchange failed ({resp.status_code})",
                code="IAM_EXCHANGE_FAILED",
            )
        data = resp.json()
        _iam_token = str(data["access_token"])
        _iam_expires_at = time.time() + int(data.get("expires_in", 3600))
        assert _iam_token is not None
        return _iam_token


async def _generate_text(
    prompt: str,
    *,
    model_id: str | None = None,
    max_new_tokens: int = 256,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Call watsonx.ai text generation API."""
    if not WATSONX_PROJECT_ID:
        raise ToolError("WATSONX_PROJECT_ID is not set", code="CONFIG_MISSING")

    model = model_id or WATSONX_DEFAULT_MODEL
    _assert_model_allowed(model)

    token = await _get_iam_token()

    body = {
        "model_id": model,
        "input": prompt,
        "project_id": WATSONX_PROJECT_ID,
        "parameters": {
            "decoding_method": "greedy" if temperature == 0 else "sample",
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
        },
    }

    async with httpx.AsyncClient(base_url=WATSONX_URL.rstrip("/"), timeout=TIMEOUT_S) as http:
        resp = await http.post(
            "/ml/v1/text/generation?version=2024-05-31",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=body,
        )
        if resp.status_code >= 400:
            resp.text[:500]
            raise ToolError(
                f"watsonx generation failed ({resp.status_code})",
                code="WATSONX_GENERATION_FAILED",
            )
        return resp.json()


@registry.register(
    "granite_summarize_paragraph",
    description="Summarize one COBOL paragraph in three sentences using Granite Code.",
    input_schema={
        "type": "object",
        "properties": {
            "program": {"type": "string"},
            "paragraph": {"type": "string"},
            "shop": {"type": "string", "default": "meridianbank"},
        },
        "required": ["program", "paragraph"],
        "additionalProperties": False,
    },
)
async def granite_summarize_paragraph(
    program: str, paragraph: str, shop: str = "meridianbank"
) -> dict[str, Any]:
    """Summarize a COBOL paragraph using Granite Code."""
    prompt = f"""You are a mainframe COBOL expert for {shop}. Summarize the following COBOL paragraph in exactly three clear sentences.

Program: {program}
Paragraph: {paragraph}

Provide a concise summary that explains what this paragraph does, focusing on business logic and data flow."""

    result = await _generate_text(prompt, max_new_tokens=200, temperature=0.2)

    return {
        "program": program,
        "paragraph": paragraph,
        "shop": shop,
        "summary": result.get("results", [{}])[0].get("generated_text", "").strip(),
        "model_id": result.get("model_id"),
        "token_count": result.get("results", [{}])[0].get("generated_token_count", 0),
    }


@registry.register(
    "granite_explain_field",
    description="Explain what a field is and where it is used, with shop-aware vocabulary.",
    input_schema={
        "type": "object",
        "properties": {
            "field_name": {"type": "string"},
            "context": {"type": "string", "description": "surrounding source"},
            "shop": {"type": "string", "default": "meridianbank"},
        },
        "required": ["field_name", "context"],
        "additionalProperties": False,
    },
)
async def granite_explain_field(
    field_name: str, context: str, shop: str = "meridianbank"
) -> dict[str, Any]:
    """Explain a COBOL field using Granite Code."""
    prompt = f"""You are a mainframe COBOL expert for {shop}. Explain the field '{field_name}' based on the following context.

Context:
{context}

Provide a clear explanation of:
1. What this field represents
2. Its data type and structure
3. How it's used in the code"""

    result = await _generate_text(prompt, max_new_tokens=300, temperature=0.2)

    return {
        "field_name": field_name,
        "shop": shop,
        "explanation": result.get("results", [{}])[0].get("generated_text", "").strip(),
        "model_id": result.get("model_id"),
        "token_count": result.get("results", [{}])[0].get("generated_token_count", 0),
    }


def main() -> int:
    return run_cli(registry, sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
