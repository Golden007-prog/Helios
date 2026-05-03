"""Dump the FastAPI app's OpenAPI document to shared/schemas/api.openapi.json.

Runs the backend in test mode (in-memory Cloudant + watsonx stub) so no
credentials are required. Sorted-key JSON output makes diffs reviewable.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "shared" / "schemas" / "api.openapi.json"

# Make sure the backend is importable. Backend lives under <repo>/backend.
sys.path.insert(0, str(REPO_ROOT / "backend"))

# Force in-memory mode so this script needs no live deps.
os.environ.setdefault("ENABLE_CLOUDANT", "true")
os.environ.setdefault("ENABLE_WATSONX", "true")
os.environ.setdefault("CLOUDANT_URL", "")
os.environ.setdefault("CLOUDANT_APIKEY", "")
os.environ.setdefault("WATSONX_APIKEY", "")
os.environ.setdefault("WATSONX_PROJECT_ID", "")
os.environ.setdefault("JWT_SECRET", "codegen-secret-not-used")


def main() -> int:
    from app.main import create_app  # noqa: E402

    app = create_app()
    schema = app.openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
