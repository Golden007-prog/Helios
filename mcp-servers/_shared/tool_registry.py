"""Tiny tool-registration shim shared by every Helios MCP server.

Why a shim instead of using the ``mcp`` SDK directly?

* The SDK couples tool registration to a live JSON-RPC stdio loop. We want
  a synchronous ``--list-tools`` mode for smoke tests and CI lint.
* Each Helios MCP server keeps its tool definitions in plain Python objects
  here, then surfaces them either through the SDK (when stdio is started)
  or through the introspection CLI.

Bob's responsibility — when activating a server in Phase 1.1+ — is to wire
the registry to the ``mcp`` SDK ``Server`` instance. The shim does not
implement the JSON-RPC protocol itself.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

ToolHandler = Callable[..., Any | Awaitable[Any]]


class ToolError(Exception):
    """Raised by a tool to signal a structured user-visible error."""

    def __init__(self, message: str, *, code: str = "TOOL_ERROR") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler
    output_schema: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)

    async def call(self, arguments: dict[str, Any]) -> Any:
        result = self.handler(**arguments)
        if inspect.isawaitable(result):
            return await result
        return result


@dataclass
class ToolRegistry:
    server_name: str
    description: str
    tools: list[Tool] = field(default_factory=list)

    def register(
        self,
        name: str,
        *,
        description: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> Callable[[ToolHandler], ToolHandler]:
        """Decorator: ``@registry.register("name", description=..., input_schema=...)``."""

        def _wrap(fn: ToolHandler) -> ToolHandler:
            self.tools.append(
                Tool(
                    name=name,
                    description=description,
                    input_schema=input_schema,
                    output_schema=output_schema,
                    handler=fn,
                    tags=list(tags or []),
                )
            )
            return fn

        return _wrap

    def names(self) -> list[str]:
        return [t.name for t in self.tools]

    def get(self, name: str) -> Tool:
        for t in self.tools:
            if t.name == name:
                return t
        raise ToolError(f"Unknown tool {name!r}", code="TOOL_NOT_FOUND")

    def to_dict(self) -> dict[str, Any]:
        return {
            "server": self.server_name,
            "description": self.description,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                    "output_schema": t.output_schema,
                    "tags": t.tags,
                }
                for t in self.tools
            ],
        }


def run_cli(registry: ToolRegistry, argv: list[str] | None = None) -> int:
    """Entrypoint shared by every server's ``__main__``.

    * ``--list-tools``       — print JSON of registered tools, exit 0.
    * ``--call <name> --args <json>`` — invoke one tool and print its result.
    * (no flag)              — start the stdio MCP loop if the ``mcp`` SDK is
                               available; otherwise print a helpful message
                               and exit non-zero.
    """
    parser = argparse.ArgumentParser(prog=registry.server_name)
    parser.add_argument("--list-tools", action="store_true", help="dump tool registry as JSON")
    parser.add_argument("--call", metavar="NAME", help="invoke a single tool")
    parser.add_argument("--args", metavar="JSON", default="{}", help="JSON arguments for --call")
    args = parser.parse_args(argv)

    if args.list_tools:
        print(json.dumps(registry.to_dict(), indent=2))
        return 0

    if args.call:
        tool = registry.get(args.call)
        try:
            arguments = json.loads(args.args or "{}")
        except json.JSONDecodeError as exc:
            print(f"--args must be JSON: {exc}", file=sys.stderr)
            return 2
        try:
            result = asyncio.run(tool.call(arguments))
        except ToolError as exc:
            print(
                json.dumps({"error": {"code": exc.code, "message": exc.message}}), file=sys.stderr
            )
            return 1
        print(json.dumps(result, default=str, indent=2))
        return 0

    return _start_stdio(registry)


def _start_stdio(registry: ToolRegistry) -> int:
    try:
        from mcp.server import Server  # type: ignore[import-not-found]
        from mcp.server.stdio import stdio_server  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        print(
            f"[{registry.server_name}] mcp SDK not installed — "
            "boot in --list-tools mode for smoke tests, or "
            "`pip install mcp` to enable the stdio loop.",
            file=sys.stderr,
        )
        return 78  # EX_CONFIG

    async def _run() -> None:
        srv: Any = Server(registry.server_name)

        @srv.list_tools()  # type: ignore[misc]
        async def _list() -> list[dict[str, Any]]:
            return [
                {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
                for t in registry.tools
            ]

        @srv.call_tool()  # type: ignore[misc]
        async def _call(name: str, arguments: dict[str, Any]) -> Any:
            tool = registry.get(name)
            return await tool.call(arguments)

        async with stdio_server() as (rx, tx):
            await srv.run(rx, tx, srv.create_initialization_options())

    asyncio.run(_run())
    return 0
