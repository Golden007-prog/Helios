"""ABEND Archaeologist core — Bob territory.

The classifier ingests raw SYSLOG / JESYSMSG / CEEDUMP text and returns the
identified ABEND, failing step, source trace, ranked root causes, and matching
runbooks. It is the third hero feature; Bob owns the inference pipeline.

Pattern library + family taxonomy are seeded in Cloudant (``helios_abend_patterns``)
and are read by Bob's implementation through the Cloudant client.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.abend import AbendResponse


@dataclass
class AbendInput:
    raw_text: str
    region: str
    job_name: str


def classify(input: AbendInput) -> AbendResponse:
    """Run the full ABEND analysis pipeline.

    BOB: implement per docs/PHASE_PLAN.md §1.4 + docs/ABEND_PATTERN_LIBRARY.md.

    Required behavior:

    * ``make abend-smoke`` (S0C7 in CUSTPROC) returns the seeded answer.
    * ``make abend-smoke-degraded`` returns ``degraded=true`` with an
      unfamiliar-tier identification when the pattern is novel.
    * Granite Code summary returns within the P95 budget (3 s) per
      docs/TESTING.md §5.
    * Confidence tiers — confirmed / probable / unfamiliar / unknown —
      gate downstream actions per docs/ABEND_PATTERN_LIBRARY.md.
    """
    raise NotImplementedError(
        "BOB: implement ABEND inference pipeline (docs/ABEND_PATTERN_LIBRARY.md)"
    )
