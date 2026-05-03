"""Seed a running Helios backend via its public API.

Used by Phase 3 local-e2e validation when the backend is in in-memory mode
and the seed script can't reach the running process's dict directly.

Usage:
    BACKEND_URL=http://localhost:8090 \
    PASSWORD=helios2026 \
    python bench/seed_running_server.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGIONS_DIR = REPO_ROOT / "shared" / "sample-corpus" / "regions"

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8090")
PASSWORD = os.environ.get("PASSWORD", "helios2026")


def login() -> str:
    r = httpx.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": "maya@meridianbank.demo", "password": PASSWORD},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["data"]["token"]


def seed_regions(token: str) -> int:
    files = sorted(REGIONS_DIR.glob("*.yaml"))
    if not files:
        raise RuntimeError(f"no region YAMLs under {REGIONS_DIR}")
    headers = {"Authorization": f"Bearer {token}"}
    count = 0
    for f in files:
        profile = yaml.safe_load(f.read_text(encoding="utf-8"))
        name = profile["name"]
        body = {"profile": profile, "reason": "phase-3 smoke seed"}
        r = httpx.post(
            f"{BACKEND_URL}/api/regions/{name}",
            json=body,
            headers=headers,
            timeout=10,
        )
        if r.status_code != 200:
            print(f"FAIL  {name}: {r.status_code} {r.text[:200]}")
            continue
        count += 1
        print(f"OK    {name}")
    return count


def smoke(token: str) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    ok = True

    # /api/regions
    r = httpx.get(f"{BACKEND_URL}/api/regions", headers=headers, timeout=10)
    regions = r.json().get("data", {}).get("regions", [])
    print(f"GET /api/regions -> {len(regions)} regions")
    ok &= len(regions) >= 7

    # /api/regions/int2/diff/int3 - 7 fields
    r = httpx.get(
        f"{BACKEND_URL}/api/regions/int2/diff/int3", headers=headers, timeout=10
    )
    fields = r.json().get("data", {}).get("fields", [])
    print(f"GET /api/regions/int2/diff/int3 -> {len(fields)} fields")
    ok &= len(fields) == 7

    # /api/score for ZBNKDEL.jcl-equivalent (we'd need to seed JCL via the
    # same trick; skipped for the running-server smoke since /api/score
    # accepts ad-hoc jcl_source too).
    payload = {
        "jcl_source": (
            "//STEP1 EXEC PGM=IDCAMS\n"
            "//SYSIN DD *\n"
            "  DELETE PROD.INT3.CUST.MASTER NONVSAM\n"
            "//\n"
        ),
        "region": "int3",
    }
    r = httpx.post(
        f"{BACKEND_URL}/api/score", json=payload, headers=headers, timeout=10
    )
    body = r.json()
    score_ok = (
        r.status_code == 200
        and isinstance(body.get("data", {}).get("score"), int)
    )
    print(
        f"POST /api/score -> status {r.status_code} score "
        f"{body.get('data', {}).get('score')}"
    )
    ok &= score_ok

    # /api/abend with seeded S0C7-shaped dump
    dump = (
        "JES2 JOB LOG\n"
        "ABEND CODE 0C7 - DATA EXCEPTION\n"
        "PSW=078D2400 8C9C2A4A\n"
        "Compile unit CUSTPROC\n"
    )
    r = httpx.post(
        f"{BACKEND_URL}/api/abend",
        json={
            "raw_text": dump,
            "context": {"region": "int3", "job_name": "CUSTPROC"},
        },
        headers=headers,
        timeout=10,
    )
    body = r.json()
    tier = body.get("data", {}).get("tier") or body.get("data", {}).get(
        "identified_abend", {}
    ).get("tier")
    print(f"POST /api/abend -> tier={tier}")
    ok &= tier in ("confirmed", "probable")

    return ok


def main() -> int:
    print(f"Seeding {BACKEND_URL}…")
    token = login()
    print("logged in OK")
    seeded = seed_regions(token)
    print(f"seeded {seeded} regions")
    print()
    print("--- integration smoke ---")
    ok = smoke(token)
    print()
    if ok:
        print("SMOKE PASS")
        return 0
    print("SMOKE FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
