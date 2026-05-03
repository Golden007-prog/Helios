"""IBM Cloud read-only MCP server.

Implements three read-only metadata tools that the deployment phase needs:

* ``list_code_engine_apps`` — apps under the configured project
* ``get_app_logs``           — recent logs for one app
* ``list_cloudant_instances``— resource service instances of type Cloudant

All three use IBM Cloud IAM exchange + the public Code Engine + Resource
Controller APIs. No write operations exposed.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx

from _shared import ToolError, ToolRegistry, run_cli

IBM_API_KEY = os.environ.get("IBM_CLOUD_API_KEY", "")
IBM_REGION = os.environ.get("IBM_CLOUD_REGION", "us-south")
CODE_ENGINE_PROJECT_ID = os.environ.get("CODE_ENGINE_PROJECT_ID", "")
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


registry = ToolRegistry(
    server_name="helios-ibm-cloud",
    description="Read-only IBM Cloud metadata (Code Engine apps + logs, Cloudant instances).",
)


async def _iam_token() -> str:
    if not IBM_API_KEY:
        raise ToolError("IBM_CLOUD_API_KEY is not set", code="CONFIG_MISSING")
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            IAM_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": IBM_API_KEY,
            },
        )
        if resp.status_code >= 400:
            raise ToolError(
                f"IAM token exchange failed ({resp.status_code})",
                code="IAM_EXCHANGE_FAILED",
            )
        return str(resp.json()["access_token"])


@registry.register(
    "list_code_engine_apps",
    description="List Code Engine apps in the configured project.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "override CODE_ENGINE_PROJECT_ID env",
            },
        },
        "additionalProperties": False,
    },
)
async def list_code_engine_apps(project_id: str | None = None) -> dict[str, Any]:
    pid = project_id or CODE_ENGINE_PROJECT_ID
    if not pid:
        raise ToolError("project_id (or CODE_ENGINE_PROJECT_ID) required", code="CONFIG_MISSING")
    token = await _iam_token()
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(
            f"https://api.{IBM_REGION}.codeengine.cloud.ibm.com/v2/projects/{pid}/apps",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        resp.raise_for_status()
        body = resp.json()
    apps = [
        {
            "name": a.get("name"),
            "status": a.get("status"),
            "image_reference": a.get("image_reference"),
            "endpoint": a.get("endpoint"),
            "scale_min_instances": a.get("scale_min_instances"),
            "scale_max_instances": a.get("scale_max_instances"),
        }
        for a in body.get("apps", [])
    ]
    return {"apps": apps, "total": len(apps), "project_id": pid}


@registry.register(
    "get_app_logs",
    description="Fetch the most-recent log lines for one Code Engine app.",
    input_schema={
        "type": "object",
        "properties": {
            "app_name": {"type": "string"},
            "tail": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 200},
            "project_id": {"type": "string"},
        },
        "required": ["app_name"],
        "additionalProperties": False,
    },
)
async def get_app_logs(
    app_name: str, tail: int = 200, project_id: str | None = None
) -> dict[str, Any]:
    pid = project_id or CODE_ENGINE_PROJECT_ID
    if not pid:
        raise ToolError("project_id (or CODE_ENGINE_PROJECT_ID) required", code="CONFIG_MISSING")
    token = await _iam_token()
    tail = min(max(tail, 1), 1000)
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(
            f"https://api.{IBM_REGION}.codeengine.cloud.ibm.com/v2/projects/"
            f"{pid}/apps/{app_name}/logs",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={"tail": tail},
        )
        if resp.status_code == 404:
            return {"app_name": app_name, "found": False, "lines": []}
        resp.raise_for_status()
        return {
            "app_name": app_name,
            "found": True,
            "tail": tail,
            "lines": resp.json().get("lines", []),
        }


@registry.register(
    "list_cloudant_instances",
    description="List Cloudant resource service instances visible to the API key.",
    input_schema={"type": "object", "properties": {}, "additionalProperties": False},
)
async def list_cloudant_instances() -> dict[str, Any]:
    token = await _iam_token()
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(
            "https://resource-controller.cloud.ibm.com/v2/resource_instances",
            headers={"Authorization": f"Bearer {token}"},
            params={"resource_id": "cloudantnosqldb"},
        )
        resp.raise_for_status()
        body = resp.json()
    instances = [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "region": r.get("region_id"),
            "state": r.get("state"),
            "plan": r.get("resource_plan_id"),
            "url": (r.get("extensions") or {}).get("endpoints", {}).get("public"),
        }
        for r in body.get("resources", [])
    ]
    return {"instances": instances, "total": len(instances)}


def main() -> int:
    return run_cli(registry, sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
