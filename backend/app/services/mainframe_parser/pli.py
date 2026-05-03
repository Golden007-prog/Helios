"""Skeletal PL/I parser — just enough for region/copybook scope.

Extracts: PROCEDURE name, %INCLUDE statements (PL/I's COPY equivalent),
DECLARE on top-level structures, FETCH targets, EXEC SQL blocks,
EXEC CICS blocks, CALL targets. Anything more (data conversion analysis,
condition handlers) is out of scope for the corpus.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.services.mainframe_parser.gaps import GapLogger, record_gap


class IncludeStatement(BaseModel):
    name: str
    line: int


class DeclareStatement(BaseModel):
    name: str
    line: int
    based_on: str | None = None


class CallStatement(BaseModel):
    target: str
    line: int


class FetchStatement(BaseModel):
    target: str
    line: int


class ExecBlock(BaseModel):
    kind: str
    line: int
    body: str
    program_link_target: str | None = None


class PliArtifact(BaseModel):
    """AST excerpt of a PL/I source."""

    model_config = ConfigDict(extra="allow")
    procedure_name: str
    is_main: bool = False
    includes: list[IncludeStatement] = Field(default_factory=list)
    declares: list[DeclareStatement] = Field(default_factory=list)
    calls: list[CallStatement] = Field(default_factory=list)
    fetches: list[FetchStatement] = Field(default_factory=list)
    exec_blocks: list[ExecBlock] = Field(default_factory=list)
    line_count: int = 0


_PROC_RE = re.compile(
    r"\b([A-Z][A-Z0-9_]*)\s*:\s*PROC(?:EDURE)?\b(?P<rest>[^;]*);",
    re.IGNORECASE,
)
_INCLUDE_RE = re.compile(r"%INCLUDE\s+([A-Z][A-Z0-9_]*)\s*;", re.IGNORECASE)
_DECLARE_RE = re.compile(
    r"\bDCL|DECLARE\s+1\s+([A-Z][A-Z0-9_]*)\s*(?:BASED\s*\(\s*([A-Z][A-Z0-9_]*)\s*\))?",
    re.IGNORECASE,
)
_CALL_RE = re.compile(r"\bCALL\s+([A-Z][A-Z0-9_]*)\b", re.IGNORECASE)
_FETCH_RE = re.compile(r"\bFETCH\s+([A-Z][A-Z0-9_]*)\b", re.IGNORECASE)
_EXEC_BEGIN_RE = re.compile(r"\bEXEC\s+(SQL|CICS)\b", re.IGNORECASE)
_EXEC_END_RE = re.compile(r";\s*$|END[-_]EXEC", re.IGNORECASE)
_LINK_PROGRAM_RE = re.compile(r"\bLINK\s+PROGRAM\s*\(\s*'([^']+)'", re.IGNORECASE)


def _strip_comments(text: str) -> str:
    """Remove ``/* ... */`` block comments (PL/I has no line comments)."""
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)


def parse_pli(
    text: str,
    *,
    source_path: str | None = None,
    gap_logger: GapLogger | None = None,
) -> PliArtifact:
    """Parse PL/I text into a :class:`PliArtifact`."""

    line_count = len(text.splitlines())
    cleaned = _strip_comments(text)
    artifact = PliArtifact(procedure_name="UNKNOWN", line_count=line_count)

    # Procedure declaration. ``OPTIONS(MAIN)`` flags it as a main proc.
    m = _PROC_RE.search(cleaned)
    if m:
        artifact.procedure_name = m.group(1).upper()
        artifact.is_main = "MAIN" in m.group("rest").upper()
    else:
        record_gap(gap_logger, "pli", source_path or "?", "no PROCEDURE found")

    for line_no, line in _enumerate_lines(cleaned):
        for inc in _INCLUDE_RE.finditer(line):
            artifact.includes.append(IncludeStatement(name=inc.group(1).upper(), line=line_no))
        for dcl in _DECLARE_RE.finditer(line):
            name = dcl.group(1)
            if name:
                artifact.declares.append(
                    DeclareStatement(
                        name=name.upper(),
                        line=line_no,
                        based_on=(dcl.group(2) or None) and dcl.group(2).upper(),
                    )
                )
        for call in _CALL_RE.finditer(line):
            target = call.group(1).upper()
            if target in {"PROC", "PROCEDURE"}:
                continue
            artifact.calls.append(CallStatement(target=target, line=line_no))
        for fetch in _FETCH_RE.finditer(line):
            artifact.fetches.append(FetchStatement(target=fetch.group(1).upper(), line=line_no))

    # EXEC SQL / EXEC CICS blocks (PL/I terminates with ``;`` or ``END-EXEC``).
    for m in _EXEC_BEGIN_RE.finditer(cleaned):
        line_no = cleaned[: m.start()].count("\n") + 1
        kind = m.group(1).lower()
        end_m = re.search(r";", cleaned[m.end() :])
        if not end_m:
            continue
        body = cleaned[m.end() : m.end() + end_m.start()].strip()
        block = ExecBlock(kind=kind, line=line_no, body=body)
        if kind == "cics":
            link = _LINK_PROGRAM_RE.search(body)
            if link:
                block.program_link_target = link.group(1).upper()
        artifact.exec_blocks.append(block)

    return artifact


def _enumerate_lines(text: str):
    for i, line in enumerate(text.splitlines(), start=1):
        yield i, line


def parse_pli_file(path: Path | str, gap_logger: GapLogger | None = None) -> PliArtifact:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return parse_pli(text, source_path=str(p), gap_logger=gap_logger)
