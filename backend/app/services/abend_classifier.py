"""ABEND Archaeologist core — classifier + confidence-tier scoring.

The classifier ingests raw SYSLOG / JESYSMSG / CEEDUMP text and returns the
identified ABEND, failing step, source trace, ranked root causes, and
matching runbooks. Pattern matching follows the algorithm described in
docs/ABEND_PATTERN_LIBRARY.md §Pattern matching algorithm:

1. Tokenize the dump into uppercased lines.
2. For each pattern, score against its ``regex_signatures`` using:
   - Match coverage (fraction of signatures hit).
   - Position weight (matches earlier in the dump score higher).
3. The composite confidence is normalised to [0, 1].
4. Tier mapping:
   confirmed   ``>= 0.7``
   probable    ``0.4 <= c < 0.7``
   unfamiliar  ``0.2 <= c < 0.4``
   unknown     ``< 0.2``

The pattern library is normally loaded from Cloudant (``helios_abend_patterns``).
For unit tests and offline operation we fall back to the YAML bundle that
``seed_demo`` ships into Cloudant on first startup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

from app.models.abend import (
    AbendResponse,
    AbendTier,
    FailingStep,
    IdentifiedAbend,
    MatchingRunbook,
    RankedRootCause,
    SourceTrace,
)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass
class AbendInput:
    raw_text: str
    region: str
    job_name: str


# Tier thresholds — see docs/ABEND_PATTERN_LIBRARY.md.
TIER_CONFIRMED = 0.7
TIER_PROBABLE = 0.4
TIER_UNFAMILIAR = 0.2


# ---------------------------------------------------------------------------
# Pattern bundle loader
# ---------------------------------------------------------------------------

def _resolve_patterns_file() -> Path | None:
    """Find ``patterns.yaml`` under either the container layout
    (``/app/shared/...`` — Dockerfile copies ``shared/`` alongside ``app/``)
    or the dev layout (``<repo>/shared/...`` — repo root is three levels
    above ``backend/app/services/``)."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "shared" / "sample-corpus" / "abend_patterns" / "patterns.yaml",
        here.parents[3] / "shared" / "sample-corpus" / "abend_patterns" / "patterns.yaml",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


_PATTERNS_FILE = _resolve_patterns_file()


def _load_bundled_patterns() -> list[dict[str, Any]]:
    """Load the YAML pattern bundle. Cached on first call."""
    if _PATTERNS_FILE is None or not _PATTERNS_FILE.exists():
        return []
    raw = yaml.safe_load(_PATTERNS_FILE.read_text(encoding="utf-8"))
    return list(raw.get("patterns") or [])


# Module-level cache so repeated calls (the common path in tests) don't
# re-read the YAML.
_BUNDLED_CACHE: list[dict[str, Any]] | None = None


def _bundled() -> list[dict[str, Any]]:
    global _BUNDLED_CACHE
    if _BUNDLED_CACHE is None:
        _BUNDLED_CACHE = _load_bundled_patterns()
    return _BUNDLED_CACHE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(
    input: AbendInput,
    *,
    patterns: list[dict[str, Any]] | None = None,
    runbooks: list[dict[str, Any]] | None = None,
    summarize: Callable[[dict[str, Any], str], str] | None = None,
) -> AbendResponse:
    """Classify a raw dump.

    Parameters
    ----------
    input
        Tokenised dump + context (region, job).
    patterns
        Optional pre-loaded pattern list (e.g. from Cloudant). Falls back
        to the YAML bundle.
    runbooks
        Optional pre-loaded runbook list (filtered to the matched pattern's
        related_runbooks). Empty list if not provided.
    summarize
        Optional Granite-style summariser. Receives ``(matched_pattern,
        raw_text)`` and returns a plain-English explanation. The default
        composes a deterministic explanation from ``pattern.typical_causes``
        so tests are reproducible without a watsonx round-trip.
    """
    pool = patterns if patterns is not None else _bundled()
    raw = input.raw_text or ""

    if not raw.strip():
        return _empty_unknown("no_dump_text")

    ranked = _rank_patterns(raw, pool)

    # Determine whether the dump even mentions something ABEND-shaped. If
    # so, treat unmatched dumps as ``unfamiliar`` (we saw a code but can't
    # classify it); if not, ``unknown`` (we have no signal at all). This is
    # the docs/ABEND_PATTERN_LIBRARY.md §Unknown ABEND handling distinction.
    code_signal = _extract_top_code(raw) or _extract_loose_abend_token(raw)

    if not ranked:
        if code_signal:
            return _unfamiliar(code_signal)
        return _empty_unknown("no_pattern_match")

    matched, confidence = ranked[0]
    tier = _confidence_tier(confidence)

    # Top score of zero (no signature matches at all) but we did see an
    # abend-shaped token in the dump -> unfamiliar, not unknown.
    if confidence == 0.0 and code_signal:
        return _unfamiliar(code_signal)

    degraded = tier in (AbendTier.UNFAMILIAR, AbendTier.UNKNOWN)
    degraded_reason = (
        "unfamiliar_pattern"
        if tier == AbendTier.UNFAMILIAR
        else ("no_pattern_match" if tier == AbendTier.UNKNOWN else None)
    )

    if tier == AbendTier.UNKNOWN:
        identified_code = code_signal or "UNKNOWN"
    else:
        identified_code = matched.get("code", "UNKNOWN")

    failing_step = _extract_failing_step(raw)
    source_trace = _extract_source_trace(raw)

    causes = matched.get("typical_causes") or []
    ranked_causes = _ranked_root_causes(causes, confidence)
    matching_runbooks = _matching_runbooks(matched, runbooks or [])

    summarise_fn = summarize or _default_summarize
    explanation = summarise_fn(matched, raw)

    response = AbendResponse(
        identified_abend=IdentifiedAbend(
            code=identified_code,
            confidence=round(confidence, 3),
            tier=tier,
        ),
        failing_step=failing_step,
        source_trace=source_trace,
        business_rule_explanation=explanation,
        ranked_root_causes=ranked_causes,
        matching_runbooks=matching_runbooks,
        degraded=degraded,
        degraded_reason=degraded_reason,
    )
    # AbendResponse has ``extra='allow'``; surface flat aliases the UI uses.
    response_dict = response.model_dump()
    response_dict["pattern_code"] = identified_code
    response_dict["confidence"] = round(confidence, 3)
    response_dict["tier"] = tier.value
    return AbendResponse.model_validate(response_dict)


def _unfamiliar(code: str) -> AbendResponse:
    """Build the response for the "saw an abend token but can't classify"
    case — degraded, tier=unfamiliar, learning-loop CTA on the UI."""
    response = AbendResponse(
        identified_abend=IdentifiedAbend(
            code=code,
            confidence=0.25,
            tier=AbendTier.UNFAMILIAR,
        ),
        failing_step=FailingStep(),
        source_trace=SourceTrace(),
        business_rule_explanation=(
            f"ABEND token {code} found in the dump but no pattern in the "
            f"library matched it confidently. Submit a pattern via the "
            f"learning loop to populate future runs."
        ),
        ranked_root_causes=[],
        matching_runbooks=[],
        degraded=True,
        degraded_reason="unfamiliar_pattern",
    )
    response_dict = response.model_dump()
    response_dict["pattern_code"] = code
    response_dict["confidence"] = 0.25
    response_dict["tier"] = AbendTier.UNFAMILIAR.value
    return AbendResponse.model_validate(response_dict)


def _empty_unknown(reason: str) -> AbendResponse:
    response = AbendResponse(
        identified_abend=IdentifiedAbend(
            code="UNKNOWN",
            confidence=0.0,
            tier=AbendTier.UNKNOWN,
        ),
        failing_step=FailingStep(),
        source_trace=SourceTrace(),
        business_rule_explanation=(
            "No ABEND pattern matched the supplied dump."
        ),
        ranked_root_causes=[],
        matching_runbooks=[],
        degraded=True,
        degraded_reason=reason,
    )
    response_dict = response.model_dump()
    response_dict["pattern_code"] = "UNKNOWN"
    response_dict["confidence"] = 0.0
    response_dict["tier"] = AbendTier.UNKNOWN.value
    return AbendResponse.model_validate(response_dict)


# ---------------------------------------------------------------------------
# Pattern ranking
# ---------------------------------------------------------------------------


def _rank_patterns(
    raw: str, pool: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], float]]:
    """Score every pattern in ``pool`` and return them sorted by score
    descending. Score is in [0, 1]."""
    if not pool:
        return []
    upper = raw.upper()
    total_lines = max(1, len(upper.splitlines()))

    scored: list[tuple[dict[str, Any], float]] = []
    for pattern in pool:
        signatures = pattern.get("regex_signatures") or []
        if not signatures:
            continue
        score = _score_pattern(upper, signatures, total_lines)
        scored.append((pattern, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


def _score_pattern(
    upper_text: str, signatures: list[str], total_lines: int
) -> float:
    """Composite score:

    coverage = matched_signatures / total_signatures
    position = 1 - earliest_match_index / total_lines  (earlier = higher)

    score = 0.7 * coverage + 0.3 * position
    """
    matched = 0
    earliest_offset: int | None = None
    for sig in signatures:
        try:
            pat = re.compile(re.escape(sig.upper()))
        except re.error:
            continue
        m = pat.search(upper_text)
        if m is None:
            continue
        matched += 1
        if earliest_offset is None or m.start() < earliest_offset:
            earliest_offset = m.start()

    if matched == 0:
        return 0.0
    coverage = matched / len(signatures)

    # Translate offset to a rough line index for the position weight.
    if earliest_offset is None:
        position = 0.0
    else:
        line_index = upper_text[:earliest_offset].count("\n")
        position = max(0.0, 1.0 - (line_index / total_lines))

    score = 0.7 * coverage + 0.3 * position
    # Clamp.
    return max(0.0, min(1.0, score))


def _confidence_tier(confidence: float) -> AbendTier:
    if confidence >= TIER_CONFIRMED:
        return AbendTier.CONFIRMED
    if confidence >= TIER_PROBABLE:
        return AbendTier.PROBABLE
    if confidence >= TIER_UNFAMILIAR:
        return AbendTier.UNFAMILIAR
    return AbendTier.UNKNOWN


# ---------------------------------------------------------------------------
# Dump field extraction
# ---------------------------------------------------------------------------


def _extract_top_code(raw: str) -> str | None:
    """Coarse code extraction for the unknown-tier path."""
    for pat in (
        r"\bSQLCODE\s*-?(\d{3})\b",
        r"\bIGZ\d{4}[A-Z]?\b",
        r"\bIEC\d{3}I\b",
        r"\bIEF\d{3}I\b",
        r"\bABEND\s+CODE\s+S?([0-9A-F]{3,4})\b",
        r"\bS([0-9A-F]{3})\b",
        r"\bU(\d{3,4})\b",
    ):
        m = re.search(pat, raw, re.IGNORECASE)
        if m:
            return m.group(0).upper()
    return None


_LOOSE_ABEND_RE = re.compile(
    r"\bABEND\s*[=:]?\s*([A-Z0-9]{2,8})", re.IGNORECASE
)


def _extract_loose_abend_token(raw: str) -> str | None:
    """Catch-all for novel codes (e.g. ``ABEND=Z99X``) that the structured
    extractor misses. This signals ``unfamiliar_pattern`` rather than
    ``unknown`` so the learning-loop CTA fires."""
    m = _LOOSE_ABEND_RE.search(raw)
    if m is None:
        return None
    return m.group(1).upper()


def _extract_failing_step(raw: str) -> FailingStep:
    step_match = re.search(
        r"(?:^|\s)(?:STEP|FAILING\s+STEP)[:\s]+([A-Z][A-Z0-9$#@_-]{0,7})",
        raw,
        re.IGNORECASE | re.MULTILINE,
    )
    # Program name is reported under several aliases in JES / CEEDUMP output.
    # Prefer ``Compile unit <NAME>`` or ``Member <NAME>`` since those are
    # least ambiguous; fall back to ``PROGRAM=`` / ``PGM=`` syntax.
    program_match = (
        re.search(
            r"\bCompile\s+unit\s+([A-Z][A-Z0-9$#@_-]{0,7})",
            raw,
            re.IGNORECASE,
        )
        or re.search(
            r"\bMember[:\s]+([A-Z][A-Z0-9$#@_-]{0,7})",
            raw,
            re.IGNORECASE,
        )
        or re.search(
            r"\bin\s+([A-Z][A-Z0-9$#@_-]{0,7})\s*$",
            raw,
            re.IGNORECASE | re.MULTILINE,
        )
        or re.search(
            r"(?:^|\s)(?:PROGRAM|PGM)[=:\s]+([A-Z][A-Z0-9$#@_-]{0,7})",
            raw,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    offset_match = re.search(r"OFFSET\s+\+?0?[xX]?([0-9A-F]+)", raw, re.IGNORECASE)
    return FailingStep(
        step_name=step_match.group(1) if step_match else None,
        program=program_match.group(1) if program_match else None,
        offset_hex=offset_match.group(1) if offset_match else None,
    )


def _extract_source_trace(raw: str) -> SourceTrace:
    paragraph_match = re.search(
        r"PARAGRAPH[:\s]+([A-Z0-9$#@_-]+)", raw, re.IGNORECASE
    )
    field_match = re.search(
        r"(?:FAILING\s+FIELD|HIGHLIGHTED\s+FIELD|failing\s+field)[:\s]+"
        r"([A-Z][A-Z0-9$#@_-]+)",
        raw,
        re.IGNORECASE,
    )
    line_match = re.search(
        r"(?:STATEMENT|SOURCE\s+STATEMENT\s+AT\s+LINE)[:\s]+(\d+)",
        raw,
        re.IGNORECASE,
    )
    return SourceTrace(
        paragraph=paragraph_match.group(1) if paragraph_match else None,
        highlighted_field=field_match.group(1) if field_match else None,
        line=int(line_match.group(1)) if line_match else None,
    )


# ---------------------------------------------------------------------------
# Root cause + runbook composition
# ---------------------------------------------------------------------------


def _ranked_root_causes(
    causes: list[str], top_confidence: float
) -> list[RankedRootCause]:
    """Distribute the top-pattern confidence across its typical causes,
    decaying with index. Prior counts are placeholders until learning
    events are wired in. The first cause carries the full top confidence;
    subsequent causes attenuate by 0.85 each step."""
    out: list[RankedRootCause] = []
    decay = top_confidence
    for i, cause in enumerate(causes):
        out.append(
            RankedRootCause(
                cause=cause,
                prior_count=max(1, 50 - i * 10),
                confidence=round(max(0.0, min(1.0, decay)), 3),
            )
        )
        decay *= 0.85
    return out


def _matching_runbooks(
    matched: dict[str, Any], runbooks: list[dict[str, Any]]
) -> list[MatchingRunbook]:
    related = set(matched.get("related_runbooks") or [])
    out: list[MatchingRunbook] = []
    for rb in runbooks:
        rb_id = str(rb.get("_id") or rb.get("id") or "")
        rb_id_short = rb_id.split(":")[-1] if rb_id else ""
        if rb_id_short and (rb_id_short in related or rb_id in related):
            out.append(
                MatchingRunbook(
                    id=rb_id,
                    title=str(rb.get("title") or rb_id_short),
                    success_count=int(rb.get("success_count") or 0),
                )
            )
    if out:
        return out
    # Fall back to a synthetic runbook handle so the UI has something to
    # render even when no Cloudant runbooks are provided.
    code = matched.get("code")
    if code and matched.get("related_runbooks"):
        return [
            MatchingRunbook(
                id=str(matched["related_runbooks"][0]),
                title=f"Runbook: {code} resolution playbook",
                success_count=0,
            )
        ]
    return []


def _default_summarize(matched: dict[str, Any], _raw: str) -> str:
    """Deterministic summary used when no Granite client is injected."""
    code = matched.get("code", "UNKNOWN")
    causes = matched.get("typical_causes") or []
    if not causes:
        return f"{code} matched the dump but no typical-cause priors are available."
    leading = causes[0]
    if len(causes) == 1:
        return f"{code}: {leading}."
    return (
        f"{code}: most likely cause is {leading}. "
        f"Other priors: {'; '.join(causes[1:3])}."
    )
