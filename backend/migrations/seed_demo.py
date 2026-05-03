"""Idempotent seed for the MeridianBank demo corpus.

Loads:
* 4 demo users (Maya, Anil, Raj, service)
* 7 region profiles from ``shared/sample-corpus/regions/*.yaml``
* CUST_DELETE_INACTIVE.JCL hero job from ``shared/sample-corpus/jcl/``
* 15 ABEND patterns from ``shared/sample-corpus/abend_patterns/patterns.yaml``
* 3 runbooks from ``shared/sample-corpus/runbooks/*.md``
* 9 prior learning events on JJ-COPYBOOK-DRIFT-001 (7 dismiss + 2 accept)
  so the dissent banner reads "your shop dismissed this 7 of 9 times".

Re-running is safe: every doc has a deterministic ``_id`` so the second
call performs an upsert (or no-op if the document is byte-identical).

Usage:
    python -m migrations.seed_demo
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from app.config import get_settings
from app.services.cloudant import CloudantClient

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = REPO_ROOT / "shared" / "sample-corpus"
REGIONS_DIR = CORPUS_ROOT / "regions"
JCL_DIR = CORPUS_ROOT / "jcl"
PATTERNS_FILE = CORPUS_ROOT / "abend_patterns" / "patterns.yaml"
RUNBOOKS_DIR = CORPUS_ROOT / "runbooks"

SHOP = "meridianbank"


def _now() -> datetime:
    return datetime.now(UTC)


def _ts(now: datetime) -> tuple[str, int]:
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z"), int(
        now.timestamp() * 1000
    )


# ---------------------------------------------------------------------------
# Static seed data (users + dissent events). Region profiles + ABEND patterns
# + runbooks are loaded from disk (single source of truth = the corpus).
# ---------------------------------------------------------------------------

USERS = [
    {
        "_id": "user:maya@meridianbank.demo",
        "kind": "user",
        "email": "maya@meridianbank.demo",
        "display_name": "Maya Patel",
        "roles": ["developer"],
    },
    {
        "_id": "user:anil@meridianbank.demo",
        "kind": "user",
        "email": "anil@meridianbank.demo",
        "display_name": "Anil Verma",
        "roles": ["reviewer", "developer"],
    },
    {
        "_id": "user:raj@meridianbank.demo",
        "kind": "user",
        "email": "raj@meridianbank.demo",
        "display_name": "Raj Iyer",
        "roles": ["admin", "reviewer", "developer"],
    },
    {
        "_id": "user:svc@meridianbank.demo",
        "kind": "user",
        "email": "svc@meridianbank.demo",
        "display_name": "Helios Service",
        "roles": ["service"],
    },
]


HERO_JCL_NAME = "CUST_DELETE_INACTIVE"


async def _seed_users(cloudant: CloudantClient) -> int:
    for user in USERS:
        await cloudant.put("users", {**user, "shop": SHOP, "schema_version": "1.0"})
    return len(USERS)


async def _seed_regions(cloudant: CloudantClient) -> int:
    """Load every region YAML from disk and upsert into helios_regions."""
    if not REGIONS_DIR.exists():
        raise FileNotFoundError(f"region corpus directory missing: {REGIONS_DIR}")
    files = sorted(REGIONS_DIR.glob("*.yaml"))
    if not files:
        raise RuntimeError(f"no region YAMLs under {REGIONS_DIR}")
    for f in files:
        profile = yaml.safe_load(f.read_text(encoding="utf-8"))
        if not isinstance(profile, dict):
            raise RuntimeError(f"{f}: top-level YAML must be a mapping")
        name = profile["name"]
        doc = {
            "_id": f"region:{SHOP}:{name}",
            "kind": "region",
            "schema_version": "1.0",
            "shop": SHOP,
            **profile,
        }
        await cloudant.put("regions", doc)
    return len(files)


async def _seed_hero_jcl(cloudant: CloudantClient) -> str:
    """Seed CUST_DELETE_INACTIVE.JCL into helios_jcl_artifacts (region=int2)."""
    src = (JCL_DIR / "CUST_DELETE_INACTIVE.JCL").read_text(encoding="utf-8")
    now = _now()
    ts_iso, ts_ms = _ts(now)
    await cloudant.put(
        "jcl_artifacts",
        {
            "_id": f"jcl:{SHOP}:{HERO_JCL_NAME}:int2",
            "kind": "jcl_artifact",
            "schema_version": "1.0",
            "shop": SHOP,
            "name": HERO_JCL_NAME,
            "region": "int2",
            "state": "open",
            "source": src,
            "owner": "maya@meridianbank.demo",
            "ts": ts_iso,
            "ts_unix_ms": ts_ms,
        },
    )
    return HERO_JCL_NAME


async def _seed_abend_patterns(cloudant: CloudantClient) -> int:
    """Load patterns.yaml and upsert each into helios_abend_patterns."""
    payload = yaml.safe_load(PATTERNS_FILE.read_text(encoding="utf-8"))
    patterns = payload["patterns"]
    for p in patterns:
        code = p["code"]
        doc = {
            "_id": f"pattern:{SHOP}:{code}",
            "kind": "abend_pattern",
            "schema_version": "1.0",
            "shop": SHOP,
            "abend_code": code,
            **{k: v for k, v in p.items() if k != "code"},
        }
        await cloudant.put("abend_patterns", doc)
    return len(patterns)


async def _seed_runbooks(cloudant: CloudantClient) -> int:
    """Each .md file becomes one runbook entry."""
    files = sorted(RUNBOOKS_DIR.glob("*.md"))
    # Map filename → applies_to so the runbook ranker has structured priors.
    applies_map = {
        "S0C7_CUSTPROC_age_calc.md": [
            {"abend_code": "S0C7", "program": "CUSTPROC", "paragraph": "2300-CALC-RETIREMENT"}
        ],
        "SQLCODE_805_int2_bind.md": [{"abend_code": "SQLCODE-805", "program": "CUSTDEL"}],
        "IEC141I_member_not_found.md": [{"abend_code": "IEC141I", "program": None}],
    }
    for f in files:
        title = f.stem.replace("_", " ")
        body = f.read_text(encoding="utf-8")
        applies = applies_map.get(f.name, [])
        await cloudant.put(
            "runbooks",
            {
                "_id": f"runbook:{SHOP}:{f.stem}",
                "kind": "runbook",
                "schema_version": "1.0",
                "shop": SHOP,
                "title": title,
                "body_markdown": body,
                "applies_to": applies,
                "fix_actions": [],
                "created_by": "system",
                "success_count": 0,
                "failure_count": 0,
            },
        )
    return len(files)


async def _seed_learning_events(cloudant: CloudantClient) -> int:
    """9 historical learning events on JJ-COPYBOOK-DRIFT-001 (7 dismiss + 2 accept).

    Each event has a deterministic ``_id`` so re-runs are no-ops.
    """
    base = _now() - timedelta(days=30)
    events: list[dict] = []
    for i in range(7):
        ts = base + timedelta(days=i * 2)
        ts_iso, ts_ms = _ts(ts)
        events.append(
            {
                "_id": f"lrn:{SHOP}:JJ-COPYBOOK-DRIFT-001:dismiss:{i}",
                "kind": "learning_event",
                "schema_version": "1.0",
                "shop": SHOP,
                "type": "feedback_jjscan_dismissed",
                "rule_id": "JJ-COPYBOOK-DRIFT-001",
                "decision": "dismiss",
                "reason_tags": ["accepted_drift"],
                "actor": "maya@meridianbank.demo",
                "ts": ts_iso,
                "ts_unix_ms": ts_ms,
            }
        )
    for i in range(2):
        ts = base + timedelta(days=14 + i * 2)
        ts_iso, ts_ms = _ts(ts)
        events.append(
            {
                "_id": f"lrn:{SHOP}:JJ-COPYBOOK-DRIFT-001:accept:{i}",
                "kind": "learning_event",
                "schema_version": "1.0",
                "shop": SHOP,
                "type": "feedback_jjscan_accept",
                "rule_id": "JJ-COPYBOOK-DRIFT-001",
                "decision": "accept",
                "reason_tags": [],
                "actor": "anil@meridianbank.demo",
                "ts": ts_iso,
                "ts_unix_ms": ts_ms,
            }
        )
    for ev in events:
        await cloudant.put("learning", ev)
    return len(events)


async def main() -> int:
    settings = get_settings()
    cloudant = CloudantClient(settings)

    for db in [
        "users",
        "regions",
        "jcl_artifacts",
        "findings",
        "audit_log",
        "abend_events",
        "abend_patterns",
        "runbooks",
        "queue",
        "learning",
        "sessions",
        "jjscan_jobs",
    ]:
        await cloudant.ensure_database(db)
        print(f"db ready        helios_{db}")

    print(f"seeded users    {await _seed_users(cloudant)}")
    print(f"seeded regions  {await _seed_regions(cloudant)}")
    print(f"seeded jcl      {await _seed_hero_jcl(cloudant)}")
    print(f"seeded patterns {await _seed_abend_patterns(cloudant)}")
    print(f"seeded runbooks {await _seed_runbooks(cloudant)}")
    print(f"seeded learning {await _seed_learning_events(cloudant)}")

    await cloudant.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
