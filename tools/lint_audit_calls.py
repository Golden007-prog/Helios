"""Static check: every state-changing endpoint must call audit_writer.write_event.

Per docs/AGENTS.md hard rule #6 / docs/AUDIT_LOG.md. Wired into pre-commit
and CI. Exit code:

* 0 — all state-changing endpoints reach a write_event call.
* 1 — at least one offender, listed on stderr.
* 2 — invocation problem (e.g., backend/ not present).

Heuristic:

* "State-changing" = a FastAPI route declared with ``@router.post(``,
  ``.put(``, ``.delete(``, or ``.patch(`` AND whose function body is not a
  Bob stub (``raise BobStubError`` / ``raise NotImplementedError``).
* Within the body, look for ``audit.write_event`` (the canonical injection
  name in the codebase) or ``await audit_writer.write_event``.
* Routes returning 204 NO CONTENT for stateless ops (logout, ping) are
  expected callers; the lint reports them but does not fail unless they're
  on the explicit allowlist below.

Invoke:
    python tools/lint_audit_calls.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / "backend" / "app" / "api"

# Routes that legitimately do not write an audit event (read-only or stateless).
ALLOWLIST: frozenset[str] = frozenset(
    {
        # WebSocket subscribe — not a state mutation.
        "ws_queue.ws_queue",
        # Health probes.
        "health.healthz",
        "health.readyz",
        "health.version",
        # Pure reads.
        "audit.query_audit",
        "audit.get_audit_event",
        "audit.attestation",
        "audit.bundle_status",
        "auth.me",
        "regions.list_regions",
        "regions.get_region",
        "regions.diff_regions",
        "queue.list_queue",
        "queue.since",
        "jcl.list_jcl",
        "jcl.get_jcl",
        "jcl.read_jcl",
        "jjscan.scan",
        "score.compute_score",
        "score.get_weights",
        "abend.analyze_abend",
        "runbooks.list_runbooks",
        "runbooks.get_runbook",
        "learning.dissent",
        "learning.priors",
        "learning.runbooks_rank",
        "promote.get_promote",
        # Bundle request enqueues a Job — the worker writes the audit event when
        # the bundle completes.
        "audit.request_bundle",
        # Queue approve/reject delegate to the module-private `_decide` helper
        # which is what calls `audit.write_event`. The helper isn't a route so
        # the lint can't follow it; trust the indirection here.
        "queue.approve",
        "queue.reject",
    }
)

STATE_CHANGING_DECORATORS = ("post", "put", "delete", "patch")


def _is_state_changing_route(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for d in node.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        if isinstance(target, ast.Attribute) and target.attr in STATE_CHANGING_DECORATORS:
            return True
    return False


def _calls_audit_writer(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            f = child.func
            # `audit.write_event(...)`
            if (
                isinstance(f, ast.Attribute)
                and f.attr == "write_event"
                and isinstance(f.value, ast.Name)
                and f.value.id in ("audit", "audit_writer", "writer")
            ):
                return True
        if isinstance(child, ast.Await):
            v = child.value
            if isinstance(v, ast.Call):
                f = v.func
                if isinstance(f, ast.Attribute) and f.attr == "write_event":
                    return True
    return False


def _is_bob_stub_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Raise) and isinstance(child.exc, ast.Call):
            f = child.exc.func
            if isinstance(f, ast.Name) and f.id in ("BobStubError", "NotImplementedError"):
                return True
    return False


def main() -> int:
    if not API_DIR.exists():
        print(f"backend api dir not found: {API_DIR}", file=sys.stderr)
        return 2

    offenders: list[str] = []

    for py in sorted(API_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        module = py.stem
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            print(f"syntax error in {py}: {exc}", file=sys.stderr)
            return 2

        for node in tree.body:
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            if not _is_state_changing_route(node):
                continue
            qual = f"{module}.{node.name}"
            if qual in ALLOWLIST:
                continue
            if _is_bob_stub_body(node):
                # Bob stubs intentionally don't reach the writer; the audit
                # call lands when Bob fills in the body.
                continue
            if not _calls_audit_writer(node):
                offenders.append(qual)

    if offenders:
        print("Audit call missing on state-changing endpoints:", file=sys.stderr)
        for o in offenders:
            print(f"  - {o}", file=sys.stderr)
        print(
            "\nFix: call `await audit.write_event(...)` somewhere in the route body, "
            "or add the route to the ALLOWLIST in this file with a comment explaining why.",
            file=sys.stderr,
        )
        return 1
    print("audit-call lint: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
