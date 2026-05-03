"""Convert backend Pydantic models to TypeScript types.

Walks every module under ``backend/app/models/`` and emits one TS file:
``frontend/src/lib/api/types.gen.ts``.

Implementation strategy: rely on ``Model.model_json_schema()`` for each
Pydantic class (Pydantic v2 produces draft-7 JSON Schema), then run a
small JSON-Schema-to-TS converter inline. We keep the converter narrow —
it handles every shape Helios actually uses (object, $ref, anyOf, enum,
array). If a future model uses a feature we don't support, the converter
emits ``unknown`` with a ``// FIXME(typegen): …`` comment so the gap is
visible at PR time.

This is deliberately not pulled from a third-party dep — it sees only
Helios's own models and is small enough to live in-tree.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "frontend" / "src" / "lib" / "api" / "types.gen.ts"
sys.path.insert(0, str(REPO_ROOT / "backend"))


def _collect_models() -> list[type]:
    from pydantic import BaseModel

    import app.models  # type: ignore[import-not-found]

    seen: dict[str, type] = {}
    for info in pkgutil.iter_modules(app.models.__path__):
        mod = importlib.import_module(f"app.models.{info.name}")
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseModel)
                and obj is not BaseModel
                and obj.__module__.startswith("app.models")
            ):
                seen.setdefault(obj.__name__, obj)
    return sorted(seen.values(), key=lambda c: c.__name__)


def _ts_type(schema: dict[str, Any], defs: dict[str, dict[str, Any]]) -> str:
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        return ref

    if "anyOf" in schema:
        parts = [_ts_type(s, defs) for s in schema["anyOf"]]
        # Pydantic emits Optional[X] as anyOf [X, null].
        return " | ".join(p if p != "null" else "null" for p in parts)

    if "enum" in schema:
        return " | ".join(json.dumps(v) for v in schema["enum"])

    t = schema.get("type")
    if t == "array":
        return f"Array<{_ts_type(schema.get('items', {}), defs)}>"
    if t == "object":
        if "additionalProperties" in schema and isinstance(schema["additionalProperties"], dict):
            return f"Record<string, {_ts_type(schema['additionalProperties'], defs)}>"
        if "properties" in schema:
            props = schema["properties"]
            required = set(schema.get("required", []))
            inner = ", ".join(
                f"{json.dumps(k)}{'' if k in required else '?'}: {_ts_type(v, defs)}"
                for k, v in props.items()
            )
            return "{ " + inner + " }"
        return "Record<string, unknown>"
    if t == "string":
        return "string"
    if t == "integer" or t == "number":
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "null":
        return "null"
    if t is None and not schema:
        return "unknown"
    return f"unknown /* FIXME(typegen): {json.dumps(schema)} */"


def _emit_interface(name: str, schema: dict[str, Any], defs: dict[str, Any]) -> str:
    if "enum" in schema:
        union = " | ".join(json.dumps(v) for v in schema["enum"])
        return f"export type {name} = {union};\n"
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    lines = [f"export interface {name} {{"]
    for k, v in props.items():
        opt = "" if k in required else "?"
        lines.append(f"  {json.dumps(k)}{opt}: {_ts_type(v, defs)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> int:
    models = _collect_models()
    if not models:
        print("no Pydantic models found under backend/app/models", file=sys.stderr)
        return 1

    aggregated: dict[str, dict[str, Any]] = {}
    for cls in models:
        schema = cls.model_json_schema(ref_template="#/$defs/{model}")
        defs = schema.get("$defs", {})
        for d_name, d_schema in defs.items():
            aggregated.setdefault(d_name, d_schema)
        # The model itself.
        title = schema.get("title", cls.__name__)
        # Drop $defs from the body before merging.
        body = {k: v for k, v in schema.items() if k != "$defs"}
        aggregated.setdefault(title, body)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    parts: list[str] = [
        "// AUTO-GENERATED — do not edit by hand.",
        "// Source: backend/app/models/**/*.py via shared/codegen/pydantic_to_typescript.py",
        "// Run `make typegen` to regenerate.",
        "",
    ]
    for name in sorted(aggregated):
        parts.append(_emit_interface(name, aggregated[name], aggregated))

    OUTPUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(aggregated)} types)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
