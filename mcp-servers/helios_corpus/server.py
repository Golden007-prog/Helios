"""helios-corpus MCP server — STUB.

Bob territory: implement read-only tools for the MeridianBank synthetic
corpus under ``shared/sample-corpus/MERIDIANBANK/``.

Per docs/MCP_SETUP.md the tool set is:

* ``list_jcl``           — list JCL members under ``MERIDIANBANK/jcl/``
* ``read_jcl``           — read one JCL member
* ``list_cobol``         — list COBOL members under ``MERIDIANBANK/cobol/``
* ``read_cobol``         — read one COBOL member
* ``list_regions``       — list region YAMLs under ``MERIDIANBANK/regions/``
* ``get_region_profile`` — read one region YAML

Each tool registration below has a complete input schema and a ``BOB:``
NotImplementedError handler. The smoke test asserts the tool list is
present at boot — when Bob fills in the handlers, no schema changes.
"""

from __future__ import annotations

import os
import sys

from _shared import ToolRegistry, run_cli

CORPUS_ROOT = os.environ.get(
    "CORPUS_ROOT",
    os.path.join(os.environ.get("PROJECT_ROOT", ""), "shared/sample-corpus/MERIDIANBANK"),
)


registry = ToolRegistry(
    server_name="helios-corpus",
    description="Read-only access to the MeridianBank synthetic corpus.",
)


def _bob_stub(tool_name: str) -> "callable[..., None]":
    def _h(**_: object) -> None:
        raise NotImplementedError(
            f"BOB: implement helios-corpus tool {tool_name!r} "
            "(spec: docs/MCP_SETUP.md § Custom Helios servers + docs/CORPUS.md)"
        )

    return _h


registry.register(
    "list_jcl",
    description="List every JCL member under MERIDIANBANK/jcl/.",
    input_schema={"type": "object", "properties": {}, "additionalProperties": False},
)(_bob_stub("list_jcl"))


registry.register(
    "read_jcl",
    description="Read one JCL member's source.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    },
)(_bob_stub("read_jcl"))


registry.register(
    "list_cobol",
    description="List every COBOL program under MERIDIANBANK/cobol/.",
    input_schema={"type": "object", "properties": {}, "additionalProperties": False},
)(_bob_stub("list_cobol"))


registry.register(
    "read_cobol",
    description="Read one COBOL program's source.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    },
)(_bob_stub("read_cobol"))


registry.register(
    "list_regions",
    description="List region YAML names under MERIDIANBANK/regions/.",
    input_schema={"type": "object", "properties": {}, "additionalProperties": False},
)(_bob_stub("list_regions"))


registry.register(
    "get_region_profile",
    description="Read one region YAML by name (e.g. 'int3').",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    },
)(_bob_stub("get_region_profile"))


def main() -> int:
    return run_cli(registry, sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
