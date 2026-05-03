"""Regex-based COBOL parser — narrow scope.

Extracts: PROGRAM-ID, COPY (with REPLACING noted), CALL, EXEC SQL blocks,
EXEC CICS blocks, OPEN/READ/WRITE/REWRITE/CLOSE on file names, and the
list of MOVE / COMPUTE statements that touch a numeric working-storage
field (so the ABEND classifier — Bob's stub — can later walk MOVE chains
backward).

This is not a ProLeap port; it is the smallest set of facts needed to
seed ``helios_cobol_artifacts`` and to fixture the COPYBOOK-DRIFT and
DB2-PLAN-MISMATCH rules. Programs that exercise corner cases the regex
doesn't handle (e.g., continuation hyphens mid-identifier) are recorded
through :class:`GapLogger`; the parser still returns a partial artifact.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.mainframe_parser.gaps import GapLogger, record_gap


class CopyStatement(BaseModel):
    name: str
    line: int
    replacing: str | None = None


class CallStatement(BaseModel):
    target: str
    line: int
    is_dynamic: bool = False


class ExecBlock(BaseModel):
    kind: Literal["sql", "cics"]
    line: int
    body: str
    referenced_includes: list[str] = Field(default_factory=list)
    program_link_target: str | None = None


class FileOp(BaseModel):
    op: Literal["OPEN", "READ", "WRITE", "REWRITE", "CLOSE", "DELETE", "START"]
    file_name: str
    line: int


class MoveStatement(BaseModel):
    source: str
    target: str
    line: int


class ComputeStatement(BaseModel):
    target: str
    expression: str
    line: int


class CobolArtifact(BaseModel):
    """Structured AST excerpt of a COBOL program."""

    model_config = ConfigDict(extra="allow")
    program_id: str
    copy_statements: list[CopyStatement] = Field(default_factory=list)
    call_statements: list[CallStatement] = Field(default_factory=list)
    exec_blocks: list[ExecBlock] = Field(default_factory=list)
    file_ops: list[FileOp] = Field(default_factory=list)
    moves: list[MoveStatement] = Field(default_factory=list)
    computes: list[ComputeStatement] = Field(default_factory=list)
    select_files: dict[str, str] = Field(default_factory=dict)
    line_count: int = 0
    has_sql: bool = False
    has_cics: bool = False


# ---------------------------------------------------------------------------
# Line classification
# ---------------------------------------------------------------------------

# COBOL fixed-format columns:
#   1-6  sequence
#   7    indicator (* = comment, - = continuation, D = debug)
#   8-72 content
# Free-format (cobol-check samples) drops the 1-6 area.


def _strip_to_logical(line: str) -> tuple[str, str]:
    """Return ``(indicator, content)`` for a COBOL line.

    For fixed-format input the indicator is column 7 and content is 8-72.
    For free-format input we return ``(' ', stripped)``.
    """
    if not line:
        return " ", ""
    raw = line.rstrip("\r\n")
    if len(raw) >= 7 and raw[:6].rstrip().isdigit():
        return raw[6], raw[7:72] if len(raw) >= 72 else raw[7:]
    if len(raw) >= 7 and raw[6] in "*/-D":
        return raw[6], raw[7:72] if len(raw) >= 72 else raw[7:]
    return " ", raw.lstrip()


# ---------------------------------------------------------------------------
# Pattern set
# ---------------------------------------------------------------------------

_PROGRAM_ID_RE = re.compile(r"\bPROGRAM-ID\s*\.\s*([A-Z][A-Z0-9-]*)\b", re.IGNORECASE)
_COPY_RE = re.compile(
    r"\bCOPY\s+(?P<name>[A-Z][A-Z0-9-]*)\s*"
    r"(?P<replacing>REPLACING\b[^.]+)?\s*\.",
    re.IGNORECASE | re.DOTALL,
)
_CALL_RE = re.compile(
    r"\bCALL\s+(?:'(?P<lit>[A-Z0-9-]+)'|(?P<dyn>[A-Z][A-Z0-9-]*))",
    re.IGNORECASE,
)
_EXEC_BEGIN_RE = re.compile(r"\bEXEC\s+(SQL|CICS)\b", re.IGNORECASE)
_EXEC_END_RE = re.compile(r"\bEND-EXEC\b", re.IGNORECASE)
_INCLUDE_RE = re.compile(r"\bINCLUDE\s+([A-Z][A-Z0-9-]*)", re.IGNORECASE)
_LINK_PROGRAM_RE = re.compile(r"\bLINK\s+PROGRAM\s*\(\s*'([^']+)'", re.IGNORECASE)

_FILE_OP_RE = re.compile(
    r"\b(OPEN|READ|WRITE|REWRITE|CLOSE|DELETE|START)\s+"
    r"(?:INPUT\s+|OUTPUT\s+|I-O\s+|EXTEND\s+)?"
    r"([A-Z][A-Z0-9-]*)",
    re.IGNORECASE,
)
_SELECT_RE = re.compile(
    r"\bSELECT\s+([A-Z][A-Z0-9-]*)\s+ASSIGN\s+TO\s+([A-Z0-9_-]+)",
    re.IGNORECASE,
)
_MOVE_RE = re.compile(
    r"\bMOVE\s+(.+?)\s+TO\s+([A-Z][A-Z0-9-]*(?:\s*\([^)]*\))?)",
    re.IGNORECASE,
)
_COMPUTE_RE = re.compile(
    r"\bCOMPUTE\s+([A-Z][A-Z0-9-]*)\s*=\s*([^.]+?)(?=\.|$)",
    re.IGNORECASE,
)


def parse_cobol(
    text: str,
    *,
    source_path: str | None = None,
    gap_logger: GapLogger | None = None,
) -> CobolArtifact:
    """Parse COBOL source text into a :class:`CobolArtifact`."""

    raw_lines = text.splitlines()
    artifact = CobolArtifact(program_id="UNKNOWN", line_count=len(raw_lines))

    # Build a logical-line list paired with the original line number, joining
    # continuation lines (``-`` indicator) so multi-line statements parse.
    logical: list[tuple[int, str]] = []
    cur_line: int | None = None
    cur_buf = ""
    for i, raw in enumerate(raw_lines, start=1):
        ind, content = _strip_to_logical(raw)
        if ind in ("*", "/"):
            if cur_buf and cur_line is not None:
                logical.append((cur_line, cur_buf))
                cur_buf = ""
                cur_line = None
            continue
        if ind == "-":
            cur_buf += content.lstrip()
            continue
        if cur_buf and cur_line is not None:
            logical.append((cur_line, cur_buf))
        cur_buf = content
        cur_line = i
    if cur_buf and cur_line is not None:
        logical.append((cur_line, cur_buf))

    full_text = "\n".join(line for _, line in logical)

    m = _PROGRAM_ID_RE.search(full_text)
    if m:
        artifact.program_id = m.group(1).upper()
    else:
        record_gap(gap_logger, "cobol", source_path or "?", "no PROGRAM-ID found")

    # COPY statements may span multiple lines; search the joined text.
    for m in _COPY_RE.finditer(full_text):
        # Find the original line number by counting newlines up to this match.
        line_no = full_text[: m.start()].count("\n") + 1
        artifact.copy_statements.append(
            CopyStatement(
                name=m.group("name").upper(),
                line=_logical_to_physical(logical, line_no),
                replacing=m.group("replacing").strip() if m.group("replacing") else None,
            )
        )

    # CALLs.
    for line_no, content in logical:
        for m in _CALL_RE.finditer(content):
            target = (m.group("lit") or m.group("dyn") or "").upper()
            if target:
                artifact.call_statements.append(
                    CallStatement(
                        target=target,
                        line=line_no,
                        is_dynamic=m.group("dyn") is not None,
                    )
                )

    # EXEC SQL / EXEC CICS blocks — collect until END-EXEC.
    open_block: dict | None = None
    for line_no, content in logical:
        if open_block is None:
            mb = _EXEC_BEGIN_RE.search(content)
            if mb:
                kind = mb.group(1).lower()
                open_block = {"line": line_no, "kind": kind, "body": [content[mb.end() :]]}
                # Same-line END-EXEC.
                me = _EXEC_END_RE.search(content)
                if me and me.start() > mb.end():
                    body = "\n".join(open_block["body"])
                    body = _EXEC_END_RE.split(body)[0]
                    artifact.exec_blocks.append(_finalize_exec(open_block["kind"], open_block["line"], body))
                    if kind == "sql":
                        artifact.has_sql = True
                    elif kind == "cics":
                        artifact.has_cics = True
                    open_block = None
        else:
            me = _EXEC_END_RE.search(content)
            if me:
                open_block["body"].append(content[: me.start()])
                body = "\n".join(open_block["body"])
                artifact.exec_blocks.append(_finalize_exec(open_block["kind"], open_block["line"], body))
                if open_block["kind"] == "sql":
                    artifact.has_sql = True
                elif open_block["kind"] == "cics":
                    artifact.has_cics = True
                open_block = None
            else:
                open_block["body"].append(content)
    if open_block is not None:
        record_gap(
            gap_logger,
            "cobol",
            source_path or artifact.program_id,
            f"unterminated EXEC {open_block['kind'].upper()} starting line {open_block['line']}",
        )

    # File ops & SELECTs.
    for line_no, content in logical:
        for m in _SELECT_RE.finditer(content):
            artifact.select_files[m.group(1).upper()] = m.group(2)
        for m in _FILE_OP_RE.finditer(content):
            op = m.group(1).upper()
            target = m.group(2).upper()
            if target in {"INPUT", "OUTPUT", "I", "EXTEND", "TO", "FROM", "INTO"}:
                continue
            artifact.file_ops.append(FileOp(op=op, file_name=target, line=line_no))

    # MOVE / COMPUTE.
    for line_no, content in logical:
        for m in _MOVE_RE.finditer(content):
            src = m.group(1).strip()
            tgt = m.group(2).strip().upper()
            if len(src) > 80 or len(tgt) > 60:
                continue
            artifact.moves.append(MoveStatement(source=src, target=tgt, line=line_no))
        for m in _COMPUTE_RE.finditer(content):
            artifact.computes.append(
                ComputeStatement(
                    target=m.group(1).upper(),
                    expression=m.group(2).strip(),
                    line=line_no,
                )
            )

    return artifact


def _finalize_exec(kind: str, line: int, body: str) -> ExecBlock:
    block = ExecBlock(kind=kind, line=line, body=body.strip())  # type: ignore[arg-type]
    for inc_match in _INCLUDE_RE.finditer(body):
        block.referenced_includes.append(inc_match.group(1).upper())
    if kind == "cics":
        link = _LINK_PROGRAM_RE.search(body)
        if link:
            block.program_link_target = link.group(1).upper()
    return block


def _logical_to_physical(logical: list[tuple[int, str]], logical_idx: int) -> int:
    """Map a 1-indexed logical line offset to the physical line number."""
    if 0 < logical_idx <= len(logical):
        return logical[logical_idx - 1][0]
    return logical_idx


def parse_cobol_file(path: Path | str, gap_logger: GapLogger | None = None) -> CobolArtifact:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return parse_cobol(text, source_path=str(p), gap_logger=gap_logger)
