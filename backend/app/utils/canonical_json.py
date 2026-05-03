"""RFC 8785 / JCS-flavored JSON canonicalization.

Used by the audit writer's hash chain (the canonical form is what gets
hashed, so the same logical event always produces the same bytes — which is
what makes the chain verifiable across reads).

This is a *pragmatic* implementation tuned to what the audit log actually
serializes (strings, ints, bools, None, dicts, lists). It is not a full
RFC 8785 implementation — IEEE-754 number canonicalization, in particular,
is left to ``json.dumps``'s default behavior, which produces stable output
for the integers / floats Helios emits but is not bit-identical to
canonical IEEE-754 for the corner cases the spec covers.

If we ever need true RFC 8785 (e.g., for cross-platform attestation
exports), swap this for the ``rfc8785`` package — the public API of this
module should not change.
"""

from __future__ import annotations

import json
from typing import Any


def canonicalize(obj: Any) -> str:
    """Return the canonical-JSON string for ``obj``.

    Rules applied:

    * Object keys sorted lexicographically (recursively).
    * No insignificant whitespace (``separators=(",", ":")``).
    * Unicode preserved (``ensure_ascii=False``) — RFC 8785 keeps non-ASCII
      verbatim where ``json`` defaults to escaping. The audit log carries
      free-form text fields, so this matters.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonicalize_bytes(obj: Any) -> bytes:
    """UTF-8 encoded canonical form. Convenient hash input."""
    return canonicalize(obj).encode("utf-8")
