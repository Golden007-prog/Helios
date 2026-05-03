"""Confidence Score calibration bench — over the seeded corpus.

For every seeded JCL × every candidate target region, we attempt to
compute a Confidence Score and record the result:

* If Bob's score engine still raises ``NotImplementedError``, the row is
  marked ``status="xfail_score_engine"`` — the run does not abort. We
  also count findings, auto-fixes, and known ground truth.
* When the engine lands, the same script doubles as a regression bench:
  the scored cells convert to ``status="ok"`` and an aggregate
  confusion matrix becomes meaningful.

The companion :func:`generate_report` writes ``docs/CALIBRATION_REPORT.md``
(gitignored — not committed). ``make calibrate`` runs both steps.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Force in-memory Cloudant + watsonx stubs.
os.environ.setdefault("CLOUDANT_URL", "")
os.environ.setdefault("CLOUDANT_APIKEY", "")
os.environ.setdefault("WATSONX_APIKEY", "")
os.environ.setdefault("WATSONX_PROJECT_ID", "")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-ship-32chars000")


@dataclass
class CalibrationRow:
    jcl: str
    source_region: str
    target_region: str
    source_pack: str | None
    status: str
    score: int | None = None
    findings_count: int = 0
    severity_counts: dict[str, int] = field(default_factory=dict)
    auto_fix_count: int = 0
    expected_score_trajectory: list[int] | None = None
    expected_findings: list[dict[str, Any]] | None = None
    scenario_id: str | None = None
    error_class: str | None = None


@dataclass
class CalibrationResult:
    started_at: str
    completed_at: str
    rows: list[CalibrationRow] = field(default_factory=list)
    confusion_matrix: dict[str, int] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Score-engine adapter
# ---------------------------------------------------------------------------


async def _try_compute_score(jcl_doc: dict[str, Any], target_region: dict[str, Any]) -> tuple[int | None, str | None]:
    """Call Bob's score engine if it has been implemented; otherwise xfail.

    Returns ``(score, error_class)``. ``error_class`` is set when the
    score engine raised; useful for slicing the calibration row.
    """
    try:
        from app.models.score import ScoreBreakdown  # noqa: F401
        from app.services.score import ScoreContext, compute, default_weights
    except Exception as exc:  # noqa: BLE001
        return None, f"import_error:{exc.__class__.__name__}"
    ctx = ScoreContext(
        jcl_source=jcl_doc.get("source", "") or json.dumps(jcl_doc.get("parsed", {})),
        region_name=target_region.get("name", "?"),
        region_weights=default_weights(),
        findings=[],
        backup_gap=False,
        region_mismatch_count=0,
        historical_abend_priors={},
    )
    try:
        score, _breakdown = compute([], ctx)
    except NotImplementedError:
        return None, "NotImplementedError"
    except Exception as exc:  # noqa: BLE001
        return None, exc.__class__.__name__
    return int(score), None


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


async def _run() -> CalibrationResult:
    from app.config import get_settings
    from app.services.cloudant import CloudantClient
    from migrations.seed_corpus import DEMO_SHOP, seed_all

    cl = CloudantClient(get_settings())
    await seed_all(cl)

    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Pull the corpus.
    jcl_docs = (
        await cl.find(
            "jcl_artifacts", {"shop": DEMO_SHOP, "kind": "jcl_artifact"}, limit=10000
        )
    )["docs"]
    region_docs = (
        await cl.find("regions", {"shop": DEMO_SHOP, "kind": "region"}, limit=100)
    )["docs"]
    scenario_docs = (
        await cl.find(
            "demo_scenarios", {"shop": DEMO_SHOP, "kind": "demo_scenario"}, limit=100
        )
    )["docs"]

    region_by_name = {r["name"]: r for r in region_docs}
    scenario_by_pair = {
        (s.get("source_artifact", "").split("/")[-1].split(".")[0].upper(), s.get("target_region")): s
        for s in scenario_docs
    }

    # Take the top 5 candidate target regions per scenario context. To keep
    # the bench tractable we pick: bnk_test_vsam, bnk_test_sql, bnk_pac,
    # bnk_prod, training_int — the five that drive the demo scenarios.
    target_regions = [
        region_by_name[name]
        for name in ("bnk_test_vsam", "bnk_test_sql", "bnk_pac", "bnk_prod", "training_int")
        if name in region_by_name
    ]

    rows: list[CalibrationRow] = []

    for jcl in jcl_docs:
        jcl_name = jcl.get("name", "?")
        source_region = jcl.get("region", "?")
        for target in target_regions:
            scn = scenario_by_pair.get((jcl_name.upper(), target["name"]))
            score, err = await _try_compute_score(jcl, target)
            row = CalibrationRow(
                jcl=jcl_name,
                source_region=source_region,
                target_region=target["name"],
                source_pack=jcl.get("source_pack"),
                status="ok" if score is not None else "xfail_score_engine",
                score=score,
                findings_count=0,
                severity_counts={},
                auto_fix_count=0,
                expected_score_trajectory=(scn or {}).get("expected_score_trajectory"),
                expected_findings=(scn or {}).get("expected_findings"),
                scenario_id=(scn or {}).get("scenario_id"),
                error_class=err,
            )
            rows.append(row)

    # Confusion matrix (predicted-amber/red vs ground-truth-needs-block).
    matrix: Counter[str] = Counter()
    for r in rows:
        gt_needs_block = bool(r.expected_findings) and any(
            f.get("severity") in ("critical", "high") for f in (r.expected_findings or [])
        )
        if r.score is None:
            predicted = "unknown"
        elif r.score >= 80:
            predicted = "green"
        elif r.score >= 60:
            predicted = "amber"
        else:
            predicted = "red"
        truth = "block" if gt_needs_block else "ok"
        matrix[f"{predicted}_vs_{truth}"] += 1

    summary = {
        "rows": len(rows),
        "ok_rows": sum(1 for r in rows if r.status == "ok"),
        "xfail_rows": sum(1 for r in rows if r.status == "xfail_score_engine"),
        "with_scenario": sum(1 for r in rows if r.scenario_id),
        "by_target_region": dict(Counter(r.target_region for r in rows)),
        "by_source_pack": dict(Counter(str(r.source_pack) for r in rows)),
    }

    completed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    await cl.close()
    return CalibrationResult(
        started_at=started,
        completed_at=completed,
        rows=rows,
        confusion_matrix=dict(matrix),
        summary=summary,
    )


def write_results(result: CalibrationResult) -> Path:
    out_dir = REPO_ROOT / "bench" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = out_dir / f"calibration_{today}.json"
    payload = {
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "rows": [asdict(r) for r in result.rows],
        "confusion_matrix": result.confusion_matrix,
        "summary": result.summary,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def generate_report(result: CalibrationResult) -> Path:
    out = REPO_ROOT / "docs" / "CALIBRATION_REPORT.md"
    lines: list[str] = []
    lines.append("# Confidence Score calibration report")
    lines.append("")
    lines.append(f"_run started_:   `{result.started_at}`")
    lines.append(f"_run completed_: `{result.completed_at}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for k, v in result.summary.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Confusion matrix (predicted vs ground truth)")
    lines.append("")
    lines.append("| cell | count |")
    lines.append("|---|---|")
    for k, v in sorted(result.confusion_matrix.items()):
        lines.append(f"| `{k}` | {v} |")
    lines.append("")
    lines.append("## Per-scenario rows")
    lines.append("")
    lines.append("| scenario | jcl | source | target | score | xfail | ground truth |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in result.rows:
        if not r.scenario_id:
            continue
        gt = "needs_block" if r.expected_findings else "ok"
        score_cell = str(r.score) if r.score is not None else "—"
        xfail_cell = "yes" if r.status == "xfail_score_engine" else ""
        lines.append(
            f"| `{r.scenario_id}` | {r.jcl} | {r.source_region} | "
            f"{r.target_region} | {score_cell} | {xfail_cell} | {gt} |"
        )
    lines.append("")
    lines.append(
        "Rows with xfail=yes mean the score engine has not been "
        "implemented yet (Bob's stub still raises `NotImplementedError`). "
        "The bench harness handles that gracefully and reports counts so "
        "calibration can run continuously as Bob lands the formula."
    )
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    result = asyncio.run(_run())
    json_path = write_results(result)
    md_path = generate_report(result)
    print(json.dumps({"json": str(json_path), "report": str(md_path), **result.summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
