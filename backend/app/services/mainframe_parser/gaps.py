"""Collect parser gaps and append them to ``docs/PARSER_GAPS.md``.

Parsers in this package never raise on unexpected syntax. When a real
corpus file exercises a corner case the parser doesn't handle, we record
the path, the parser, and the message; the seed loader skips that file.
This keeps the demo robust to the long tail of mainframe dialects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

def _resolve_gaps_file() -> Path:
    """Find ``docs/PARSER_GAPS.md`` under either the container layout
    (``/app/docs/...``) or the dev layout (``<repo>/docs/...``)."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "docs" / "PARSER_GAPS.md",
        here.parents[4] / "docs" / "PARSER_GAPS.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[1]


_GAPS_FILE = _resolve_gaps_file()
_LOCK = Lock()


@dataclass
class GapLogger:
    """Collects gaps in memory; flushes to ``docs/PARSER_GAPS.md`` on close."""

    entries: list[dict[str, str]] = field(default_factory=list)

    def record(self, parser: str, source_path: str, message: str) -> None:
        self.entries.append(
            {
                "parser": parser,
                "source_path": source_path,
                "message": message,
            }
        )

    def flush(self) -> Path | None:
        """Write ``docs/PARSER_GAPS.md`` if any gaps were collected."""
        if not self.entries:
            return None
        with _LOCK:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            lines: list[str] = []
            if not _GAPS_FILE.exists():
                lines.append("# Parser Gaps\n")
                lines.append(
                    "Real corpus files where one of the parsers under "
                    "`backend/app/services/mainframe_parser/` could not "
                    "produce a complete AST. The seed loader skips these "
                    "files; the demo's five hero scenarios do not depend "
                    "on them. Add a parser fix when a gap blocks a planned "
                    "scenario; until then a gap entry is the right "
                    "long-tail trade-off.\n"
                )
            lines.append(f"\n## Run {now}\n")
            for entry in self.entries:
                lines.append(
                    f"- `{entry['parser']}` — `{entry['source_path']}`: "
                    f"{entry['message']}\n"
                )
            _GAPS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with _GAPS_FILE.open("a", encoding="utf-8") as fp:
                fp.writelines(lines)
        return _GAPS_FILE


def record_gap(logger: GapLogger | None, parser: str, source_path: str, message: str) -> None:
    """Convenience for parsers — call with a logger or a ``None`` no-op."""
    if logger is None:
        return
    logger.record(parser, source_path, message)
