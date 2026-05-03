"""Convert shared/constants/*.json to a TypeScript module.

Output: ``frontend/src/lib/api/constants.gen.ts`` — re-exports every JSON
file as a typed ``as const`` object so the frontend can use the constants
without parsing JSON at runtime.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "shared" / "constants"
OUTPUT = REPO_ROOT / "frontend" / "src" / "lib" / "api" / "constants.gen.ts"


def _to_const_name(stem: str) -> str:
    return stem.upper()


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    parts: list[str] = [
        "// AUTO-GENERATED — do not edit by hand.",
        "// Source: shared/constants/*.json via shared/codegen/dump_constants.py",
        "",
    ]
    files = sorted(SRC.glob("*.json"))
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        name = _to_const_name(path.stem)
        parts.append(
            f"export const {name} = {json.dumps(data, indent=2)} as const;\n"
        )
    OUTPUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
