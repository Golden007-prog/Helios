"""Region Atlas — schema validator + diff engine + substitution engine.

The diff engine walks two ``RegionProfile`` instances in pydantic
field-declaration order and produces an ordered list of ``DiffField``
entries. The substitution engine rewrites a JCL source so its
region-specific tokens match a target region, and emits a per-change
trace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.errors import ErrorCode, HeliosError
from app.models.region import DiffField, RegionDiffResponse, RegionProfile
from app.services.cloudant import CloudantClient

DB_SHORT = "regions"


@dataclass
class SubstitutionTrace:
    """One row in the substitution audit. Each rewrite the engine performs
    appends a row so the UI can render a "what was rewritten and why" panel.
    """

    path: str  # dotted region-profile path the substitution maps to
    before: str
    after: str
    line: int  # 1-indexed JCL line number
    reason: str  # short human explanation (e.g. "HLQ rewrite")


def _trace_dict(t: SubstitutionTrace) -> dict[str, Any]:
    return {
        "path": t.path,
        "before": t.before,
        "after": t.after,
        "line": t.line,
        "reason": t.reason,
    }


async def load_region(cloudant: CloudantClient, name: str, shop: str) -> RegionProfile | None:
    """Look up a region by name. Returns None if not found."""
    result = await cloudant.find(
        DB_SHORT,
        {"shop": shop, "kind": "region", "name": name},
        limit=1,
    )
    docs = result.get("docs", [])
    if not docs:
        return None
    doc = docs[0]
    # Cloudant fields the model doesn't expect — drop them here.
    for k in ("_id", "_rev", "kind", "schema_version", "shop"):
        doc.pop(k, None)
    return RegionProfile.model_validate(doc)


async def list_regions(
    cloudant: CloudantClient, shop: str, *, tier: str | None = None
) -> list[RegionProfile]:
    sel: dict[str, Any] = {"shop": shop, "kind": "region"}
    if tier:
        sel["tier"] = tier
    result = await cloudant.find(DB_SHORT, sel, limit=100)
    out: list[RegionProfile] = []
    for doc in result.get("docs", []):
        for k in ("_id", "_rev", "kind", "schema_version", "shop"):
            doc.pop(k, None)
        out.append(RegionProfile.model_validate(doc))
    return out


async def save_region(
    cloudant: CloudantClient, profile: RegionProfile, shop: str
) -> dict[str, Any]:
    """Upsert by region name. Returns the persisted document."""
    existing = await cloudant.find(
        DB_SHORT,
        {"shop": shop, "kind": "region", "name": profile.name},
        limit=1,
    )
    doc: dict[str, Any] = {
        "kind": "region",
        "schema_version": "1.0",
        "shop": shop,
        **profile.model_dump(by_alias=True, exclude_none=False),
    }
    if existing.get("docs"):
        old = existing["docs"][0]
        doc["_id"] = old["_id"]
        doc["_rev"] = old.get("_rev")
    return await cloudant.put(DB_SHORT, doc)


def diff_regions(a: RegionProfile, b: RegionProfile) -> RegionDiffResponse:
    """Field-by-field structural diff between two region profiles.

    Order is deterministic: pydantic field-declaration order at every level
    of nesting, with dict keys (when not backed by a model) walked in
    declaration order via ``dict.keys()`` (Python 3.7+ insertion order).
    Lists are compared positionally; length deltas surface as ``added`` /
    ``removed`` entries with index suffixes (e.g. ``protected_resources[3]``).
    The top-level ``name`` field is the region identifier, not a content
    field — we surface it on the envelope (``a`` / ``b``) but skip it in
    ``fields`` so the diff describes substantive differences only.
    Returned ``DiffField`` entries are not re-sorted afterwards.
    """
    fields: list[DiffField] = []
    _walk_diff(a, b, "", fields)
    fields = [f for f in fields if f.path != "name"]
    return RegionDiffResponse(a=a.name, b=b.name, fields=fields)


def _walk_diff(obj_a: Any, obj_b: Any, path: str, out: list[DiffField]) -> None:
    """Recursively walk two objects in deterministic field-declaration order
    and append ``DiffField`` rows to ``out``.
    """
    if obj_a is None and obj_b is None:
        return
    if obj_a is None:
        out.append(DiffField(path=path, a=None, b=obj_b, kind="added"))
        return
    if obj_b is None:
        out.append(DiffField(path=path, a=obj_a, b=None, kind="removed"))
        return

    # Pydantic models — walk in field-declaration order from model_fields.
    if isinstance(obj_a, BaseModel) and isinstance(obj_b, BaseModel):
        # When the two models are the same class, model_fields is shared and
        # iteration order is the declaration order. When the classes diverge
        # (rare here), fall through to dict-based walk.
        if type(obj_a) is type(obj_b):
            for field_name in obj_a.__class__.model_fields:
                child_path = f"{path}.{field_name}" if path else field_name
                _walk_diff(
                    getattr(obj_a, field_name),
                    getattr(obj_b, field_name),
                    child_path,
                    out,
                )
            return
        # Heterogeneous models: serialize and walk as dicts.
        _walk_diff(
            obj_a.model_dump(by_alias=False, exclude_none=False),
            obj_b.model_dump(by_alias=False, exclude_none=False),
            path,
            out,
        )
        return

    # Dicts — walk insertion-order keys from a, then any keys b has that a
    # doesn't (preserves stable ordering when the two dicts are co-ordered).
    if isinstance(obj_a, dict) and isinstance(obj_b, dict):
        seen: set[str] = set()
        for key in obj_a:
            seen.add(key)
            child_path = f"{path}.{key}" if path else key
            if key not in obj_b:
                out.append(DiffField(path=child_path, a=obj_a[key], b=None, kind="removed"))
            else:
                _walk_diff(obj_a[key], obj_b[key], child_path, out)
        for key in obj_b:
            if key in seen:
                continue
            child_path = f"{path}.{key}" if path else key
            out.append(DiffField(path=child_path, a=None, b=obj_b[key], kind="added"))
        return

    # Lists — positional comparison with kind=added / removed for length deltas.
    if isinstance(obj_a, list) and isinstance(obj_b, list):
        max_len = max(len(obj_a), len(obj_b))
        for i in range(max_len):
            child_path = f"{path}[{i}]"
            if i >= len(obj_a):
                out.append(DiffField(path=child_path, a=None, b=obj_b[i], kind="added"))
            elif i >= len(obj_b):
                out.append(DiffField(path=child_path, a=obj_a[i], b=None, kind="removed"))
            else:
                # Recurse so nested dicts/models inside list items still walk
                # in field-declaration order.
                _walk_diff(obj_a[i], obj_b[i], child_path, out)
        return

    # Primitive values.
    if obj_a != obj_b:
        out.append(DiffField(path=path, a=obj_a, b=obj_b, kind="value_change"))


def apply_substitutions(
    jcl_source: str,
    source_region: RegionProfile,
    target_region: RegionProfile,
) -> tuple[str, list[dict[str, Any]]]:
    """Rewrite ``jcl_source`` so its region-specific tokens match
    ``target_region``. Returns ``(rewritten_jcl, substitution_trace)``.

    Substituted axes (each emits a row per rewritten line):

    1. HLQ prefix
    2. DB2 subsystem id (``SYSTEM(...)`` and ``SUBSYS=...`` forms)
    3. DB2 plan collection (``PLAN(...)`` / ``COLLECTION=...``)
    4. JES class (``CLASS=...`` on the JOB card)
    5. RACF user / group (``USER=...`` / ``GROUP=...``)
    6. Volser pattern (``VOL=...`` / ``VOLUME=...``)
    7. Scheduler queue (``QUEUE=...``)

    Comment lines (``//*``) are preserved untouched. Every JCL line is left
    at <= 72 characters by re-flowing only when the rewritten substring
    keeps the same length; otherwise the line is updated in-place and the
    caller is responsible for any 72-column re-flow.
    """
    if not jcl_source:
        return jcl_source, []

    lines = jcl_source.split("\n")
    traces: list[SubstitutionTrace] = []

    # ---- helpers -----------------------------------------------------
    def _is_comment(line: str) -> bool:
        # Per JCL spec, ``//*`` in cols 1-3 is a comment line.
        return line.startswith("//*")

    def _record(idx: int, before: str, after: str, path: str, reason: str) -> None:
        traces.append(
            SubstitutionTrace(
                path=path,
                before=before,
                after=after,
                line=idx + 1,
                reason=reason,
            )
        )

    def _apply_simple(
        pattern: re.Pattern[str],
        replacement: str,
        path: str,
        before: str,
        after: str,
        reason: str,
    ) -> None:
        for i, line in enumerate(lines):
            if _is_comment(line):
                continue
            new_line, n = pattern.subn(replacement, line)
            if n > 0 and new_line != line:
                lines[i] = new_line
                _record(i, before, after, path, reason)

    # 1. HLQ substitution — be careful only to rewrite when the HLQ token
    # appears at a dataset-name boundary (after an apostrophe / paren / DSN= /
    # whitespace / start-of-token), so we don't accidentally chew comment
    # narrative or program names.
    if source_region.hlq and target_region.hlq and source_region.hlq != target_region.hlq:
        hlq_pat = re.compile(
            rf"(?<![A-Z0-9.]){re.escape(source_region.hlq)}(?=[.\s,'\"\)])",
            re.IGNORECASE,
        )
        _apply_simple(
            hlq_pat,
            target_region.hlq,
            path="hlq",
            before=source_region.hlq,
            after=target_region.hlq,
            reason="HLQ rewrite to match target region",
        )

    # 2. DB2 subsystem
    if (
        source_region.db2
        and target_region.db2
        and source_region.db2.subsystem_id != target_region.db2.subsystem_id
    ):
        db2_sub = re.compile(
            rf"(\bSYSTEM\(|\bSUBSYS=){re.escape(source_region.db2.subsystem_id)}(?=[\)\,\s])",
            re.IGNORECASE,
        )
        _apply_simple(
            db2_sub,
            rf"\g<1>{target_region.db2.subsystem_id}",
            path="db2.subsystem_id",
            before=source_region.db2.subsystem_id,
            after=target_region.db2.subsystem_id,
            reason="DB2 subsystem rewrite",
        )

    # 3. DB2 plan collection
    if (
        source_region.db2
        and target_region.db2
        and source_region.db2.plan_collection != target_region.db2.plan_collection
    ):
        plan_pat = re.compile(
            rf"(\bPLAN\(|\bCOLLECTION=){re.escape(source_region.db2.plan_collection)}(?=[\)\,\s])",
            re.IGNORECASE,
        )
        _apply_simple(
            plan_pat,
            rf"\g<1>{target_region.db2.plan_collection}",
            path="db2.plan_collection",
            before=source_region.db2.plan_collection,
            after=target_region.db2.plan_collection,
            reason="DB2 plan/collection rewrite",
        )

    # 4. JES class — only rewrite the JOB card token (``CLASS=X``).
    if (
        source_region.jes
        and target_region.jes
        and source_region.jes.class_ != target_region.jes.class_
    ):
        class_pat = re.compile(
            rf"\bCLASS={re.escape(source_region.jes.class_)}(?=[\s,])",
            re.IGNORECASE,
        )
        _apply_simple(
            class_pat,
            f"CLASS={target_region.jes.class_}",
            path="jes.class",
            before=source_region.jes.class_,
            after=target_region.jes.class_,
            reason="JES class rewrite",
        )

    # 5. RACF group
    if (
        source_region.racf_group
        and target_region.racf_group
        and source_region.racf_group != target_region.racf_group
    ):
        racf_pat = re.compile(
            rf"(\bUSER=|\bGROUP=){re.escape(source_region.racf_group)}(?=[\s,])",
            re.IGNORECASE,
        )
        _apply_simple(
            racf_pat,
            rf"\g<1>{target_region.racf_group}",
            path="racf_group",
            before=source_region.racf_group,
            after=target_region.racf_group,
            reason="RACF group rewrite",
        )

    # 6. Volser pattern — strip trailing wildcard before rewriting the
    # base prefix so ``VOL=TST*`` becomes ``VOL=PRD*``.
    if (
        source_region.volser_pattern
        and target_region.volser_pattern
        and source_region.volser_pattern != target_region.volser_pattern
    ):
        src_base = source_region.volser_pattern.rstrip("*")
        tgt_base = target_region.volser_pattern.rstrip("*")
        if src_base:
            volser_pat = re.compile(
                rf"(\bVOL=|\bVOLUME=){re.escape(src_base)}",
                re.IGNORECASE,
            )
            _apply_simple(
                volser_pat,
                rf"\g<1>{tgt_base}",
                path="volser_pattern",
                before=source_region.volser_pattern,
                after=target_region.volser_pattern,
                reason="Volser pattern rewrite",
            )

    # 7. Scheduler queue
    if (
        source_region.scheduler_queue
        and target_region.scheduler_queue
        and source_region.scheduler_queue != target_region.scheduler_queue
    ):
        queue_pat = re.compile(
            rf"\bQUEUE={re.escape(source_region.scheduler_queue)}(?=[\s,])",
            re.IGNORECASE,
        )
        _apply_simple(
            queue_pat,
            f"QUEUE={target_region.scheduler_queue}",
            path="scheduler_queue",
            before=source_region.scheduler_queue,
            after=target_region.scheduler_queue,
            reason="Scheduler queue rewrite",
        )

    rewritten = "\n".join(lines)
    return rewritten, [_trace_dict(t) for t in traces]


def must_exist(profile: RegionProfile | None, name: str) -> RegionProfile:
    if profile is None:
        raise HeliosError(ErrorCode.REGION_NOT_FOUND, f"No region named '{name}'")
    return profile
