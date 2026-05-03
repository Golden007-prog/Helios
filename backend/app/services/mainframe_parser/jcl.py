"""JCL parser — extracts the structure used by JJSCAN+, the score engine,
and the cataloged-procedure parser.

This is intentionally narrow: it parses what the four seeded JJSCAN+
rules need to consume (steps, EXECs, DD statements, JCLLIB, DB2
``DSN SYSTEM`` blocks), and stops. It does not evaluate symbolic
parameters, does not unfold INCLUDE chains, and does not resolve
PROCs — those are responsibilities of the rules themselves.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.mainframe_parser.gaps import GapLogger, record_gap


class DDStatement(BaseModel):
    """A single ``//DDNAME DD ...`` line (concatenated continuations folded)."""

    model_config = ConfigDict(extra="allow")
    name: str
    raw: str
    dsn: str | None = None
    disp: str | None = None
    sysout: str | None = None
    is_dummy: bool = False
    is_instream: bool = False
    instream: list[str] = Field(default_factory=list)
    extra_params: dict[str, str] = Field(default_factory=dict)


class Step(BaseModel):
    """A ``//STEPNAME EXEC ...`` block and the DDs that follow it."""

    model_config = ConfigDict(extra="allow")
    name: str
    exec_kind: Literal["pgm", "proc"]
    exec_target: str
    exec_params: dict[str, str] = Field(default_factory=dict)
    dd_statements: list[DDStatement] = Field(default_factory=list)
    db2_systems: list["Db2RunBlock"] = Field(default_factory=list)


class Db2RunBlock(BaseModel):
    """A ``DSN SYSTEM(SUB) RUN PROGRAM(P) PLAN(PL) LIB('lib')`` block."""

    subsystem: str
    program: str
    plan: str | None = None
    lib: str | None = None
    parms: str | None = None


class JclArtifact(BaseModel):
    """Structured AST of a JCL job (or proc)."""

    model_config = ConfigDict(extra="allow")
    name: str
    kind: Literal["job", "proc"] = "job"
    job_card: dict[str, str] = Field(default_factory=dict)
    steps: list[Step] = Field(default_factory=list)
    jcllib: list[str] = Field(default_factory=list)
    includes: list[str] = Field(default_factory=list)
    proc_refs: list[str] = Field(default_factory=list)
    pgm_refs: list[str] = Field(default_factory=list)
    steplib_dsns: list[str] = Field(default_factory=list)
    proc_parameters: dict[str, str | None] = Field(default_factory=dict)
    raw_lines_count: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_LINE_OP_RE = re.compile(
    r"^//(?P<name>[\$#@A-Z0-9]*(?:\.[\$#@A-Z0-9]+)?)\s+"
    r"(?P<op>JOB|EXEC|DD|PROC|PEND|JCLLIB|INCLUDE|IF|ELSE|ENDIF|SET|OUTPUT)\b(?P<rest>.*)$",
    re.IGNORECASE,
)
# Continuation lines: ``// <continuation>``  (no name + no op keyword).
_CONT_RE = re.compile(r"^//\s+(?P<rest>\S.*)$")
_COMMENT_RE = re.compile(r"^//\*")
_INSTREAM_END_RE = re.compile(r"^//\s*$|^/\*$|^//\*")


def _strip_sequence(line: str) -> str:
    """Drop the right-margin sequence number block, if any (cols 73-80)."""
    if len(line) > 72 and line[72:].strip().isdigit():
        return line[:72]
    return line.rstrip("\r\n")


def _parse_kv(text: str) -> dict[str, str]:
    """Return a dict from ``A=1,B=2,C=(X,Y)`` style operand text.

    Honours one level of parentheses so that ``DCB=(RECFM=VB,LRECL=99)`` is
    captured as a single ``DCB`` value with the parenthesised body.
    """
    out: dict[str, str] = {}
    i = 0
    text = text.strip()
    while i < len(text):
        m = re.match(r"([A-Z][A-Z0-9]*)\s*=\s*", text[i:], re.IGNORECASE)
        if not m:
            break
        key = m.group(1).upper()
        i += m.end()
        if i < len(text) and text[i] == "(":
            depth = 0
            start = i
            while i < len(text):
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
            value = text[start:i]
        elif i < len(text) and text[i] == "'":
            j = text.find("'", i + 1)
            if j == -1:
                value = text[i:]
                i = len(text)
            else:
                value = text[i : j + 1]
                i = j + 1
        else:
            j = i
            while j < len(text) and text[j] not in ",":
                j += 1
            value = text[i:j]
            i = j
        out[key] = value.strip()
        if i < len(text) and text[i] == ",":
            i += 1
    return out


def _fold_continuations(raw: str) -> list[tuple[int, str]]:
    """Return ``[(physical_line_no, logical_line)]`` after folding ``//`` continuations.

    A continuation either ends with a comma followed by whitespace, or the
    next line is a ``// <something>`` line that is not itself a new
    statement. Comment lines (``//*``) are dropped.
    """
    folded: list[tuple[int, str]] = []
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = _strip_sequence(lines[i])
        if _COMMENT_RE.match(line):
            i += 1
            continue
        if not line.startswith("//"):
            i += 1
            continue
        physical = i + 1
        logical = line
        if _LINE_OP_RE.match(line) is None and _CONT_RE.match(line) is None:
            i += 1
            continue
        # Fold continuations: a continuation is signaled by a trailing comma.
        while logical.rstrip().endswith(",") and i + 1 < len(lines):
            i += 1
            nxt = _strip_sequence(lines[i])
            if _COMMENT_RE.match(nxt):
                continue
            cm = _CONT_RE.match(nxt)
            if cm:
                logical = logical.rstrip().rstrip(",") + "," + cm.group("rest")
                continue
            # A new statement aborts continuation; rewind.
            i -= 1
            break
        folded.append((physical, logical))
        i += 1
    return folded


def _split_operands(text: str) -> tuple[str, str]:
    """Return ``(positional, keyword_text)`` for an operands string.

    EXEC PGM=X has no positional, while EXEC PROC=Y or EXEC name has the
    proc name first. DDs may have positional ``*`` or ``DUMMY``.
    """
    text = text.strip()
    if not text:
        return "", ""
    # Split on first comma that is not inside parens or quotes.
    depth = 0
    in_quote = False
    for j, ch in enumerate(text):
        if ch == "'":
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                return text[:j].strip(), text[j + 1 :].strip()
    return text.strip(), ""


# ---------------------------------------------------------------------------
# DB2 inline DSN parser
# ---------------------------------------------------------------------------


_DB2_SYSTEM_RE = re.compile(r"DSN\s+SYSTEM\s*\(\s*([A-Z0-9]+)\s*\)", re.IGNORECASE)
_DB2_RUN_RE = re.compile(
    r"RUN\s+PROGRAM\s*\(\s*([A-Z0-9]+)\s*\)"
    r"(?:\s*\+?\s*PLAN\s*\(\s*([A-Z0-9]+)\s*\))?"
    r"(?:\s*\+?\s*LIB\s*\(\s*'([^']+)'\s*\))?"
    r"(?:\s*\+?\s*PARMS\s*\(\s*'([^']*)'\s*\))?",
    re.IGNORECASE | re.DOTALL,
)


def _scan_db2_blocks(instream: list[str]) -> list[Db2RunBlock]:
    """Find ``DSN SYSTEM(...) RUN PROGRAM(...) [PLAN(...)] [LIB(...)] [PARMS(...)]``."""
    blob = " ".join(line.lstrip() for line in instream)
    blob = blob.replace("+", " ")
    blocks: list[Db2RunBlock] = []
    for sys_match in _DB2_SYSTEM_RE.finditer(blob):
        sub = sys_match.group(1)
        tail = blob[sys_match.end() :]
        run = _DB2_RUN_RE.search(tail)
        if not run:
            continue
        blocks.append(
            Db2RunBlock(
                subsystem=sub.upper(),
                program=run.group(1).upper(),
                plan=run.group(2).upper() if run.group(2) else None,
                lib=run.group(3) or None,
                parms=run.group(4) or None,
            )
        )
    return blocks


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


def parse_jcl(
    text: str,
    *,
    name: str | None = None,
    source_path: str | None = None,
    gap_logger: GapLogger | None = None,
) -> JclArtifact:
    """Parse JCL text into a :class:`JclArtifact`.

    ``name`` defaults to the JOB name on the first ``//... JOB`` card;
    if neither is present, a synthetic name based on ``source_path`` is
    used. Continuations are folded; comments dropped; instream data
    captured for the DSN block under the DD that starts it.
    """

    folded = _fold_continuations(text)
    artifact = JclArtifact(name=name or "UNKNOWN", raw_lines_count=len(text.splitlines()))

    current_step: Step | None = None
    current_dd: DDStatement | None = None
    in_proc = False
    proc_name: str | None = None

    for physical, logical in folded:
        m = _LINE_OP_RE.match(logical)
        if not m:
            continue
        ddname = m.group("name").strip()
        op = m.group("op").upper()
        rest = m.group("rest").strip()

        # Close any open instream DD when a new statement begins.
        if current_dd and current_dd.is_instream and op != "DD":
            current_dd = None

        try:
            if op == "JOB":
                pos, kw = _split_operands(rest)
                artifact.kind = "job"
                if ddname:
                    artifact.name = ddname
                if pos:
                    artifact.job_card["accounting"] = pos
                artifact.job_card.update(_parse_kv(kw))
                continue

            if op == "PROC":
                in_proc = True
                proc_name = ddname or artifact.name
                artifact.kind = "proc"
                if ddname:
                    artifact.name = ddname
                # Parameters with default values: ``LNGPRFX='IGY630',SRC=COBOL``
                if rest:
                    for k, v in _parse_kv(rest).items():
                        artifact.proc_parameters[k] = v
                continue

            if op == "PEND":
                in_proc = False
                continue

            if op == "JCLLIB":
                # //LIBSRCH JCLLIB ORDER=(MERIDIAN.PROCLIB,SYS1.PROCLIB)
                kw = _parse_kv(rest)
                order = kw.get("ORDER", "")
                inner = order.strip("()")
                artifact.jcllib = [s.strip() for s in inner.split(",") if s.strip()]
                continue

            if op == "INCLUDE":
                kw = _parse_kv(rest)
                if "MEMBER" in kw:
                    artifact.includes.append(kw["MEMBER"])
                continue

            if op == "EXEC":
                pos, kw = _split_operands(rest)
                kvs = _parse_kv(kw)
                # Some JCLs put PGM=/PROC= in the positional slot
                # (``EXEC PGM=X``); _split_operands returned PGM=X as
                # ``pos`` because there was no comma. Re-feed it.
                if "=" in pos:
                    kvs.update(_parse_kv(pos))
                    pos = ""
                exec_kind: Literal["pgm", "proc"]
                exec_target: str
                if "PGM" in kvs:
                    exec_kind = "pgm"
                    exec_target = kvs.pop("PGM").strip("'")
                    artifact.pgm_refs.append(exec_target)
                elif "PROC" in kvs:
                    exec_kind = "proc"
                    exec_target = kvs.pop("PROC")
                    artifact.proc_refs.append(exec_target)
                else:
                    # ``EXEC procname[,parm=val]`` — positional proc reference.
                    exec_kind = "proc"
                    exec_target = pos.strip()
                    if exec_target:
                        artifact.proc_refs.append(exec_target)
                step = Step(
                    name=ddname or f"STEP{len(artifact.steps) + 1}",
                    exec_kind=exec_kind,
                    exec_target=exec_target,
                    exec_params=kvs,
                )
                artifact.steps.append(step)
                current_step = step
                current_dd = None
                continue

            if op == "DD":
                if current_step is None:
                    # Procs may have job-level DD statements (PROC default DDs).
                    if in_proc:
                        # Synthesize a hidden step.
                        synth = Step(
                            name=proc_name or "PROC",
                            exec_kind="pgm",
                            exec_target="",
                        )
                        artifact.steps.append(synth)
                        current_step = synth
                    else:
                        continue
                pos, _ = _split_operands(rest)
                kvs = _parse_kv(rest)
                dd = DDStatement(name=ddname, raw=rest)
                # Forms: ``DD *`` (instream), ``DD DUMMY``, ``DD DSN=..``,
                # ``DD DSNAME=..``, ``DD DDNAME=..``, ``DD SYSOUT=*``.
                if pos == "*":
                    dd.is_instream = True
                elif pos.upper() == "DUMMY":
                    dd.is_dummy = True
                if "DSN" in kvs:
                    dd.dsn = kvs.pop("DSN")
                if "DSNAME" in kvs and dd.dsn is None:
                    dd.dsn = kvs.pop("DSNAME")
                if "DISP" in kvs:
                    dd.disp = kvs.pop("DISP")
                if "SYSOUT" in kvs:
                    dd.sysout = kvs.pop("SYSOUT")
                dd.extra_params = kvs
                current_step.dd_statements.append(dd)
                if dd.name.upper() == "STEPLIB" and dd.dsn:
                    artifact.steplib_dsns.append(dd.dsn)
                # Concatenated DDs (``// DD ...`` with no ddname) attach to current_dd.
                current_dd = dd
                continue

            if op in {"IF", "ELSE", "ENDIF", "SET", "OUTPUT"}:
                continue
        except Exception as exc:  # noqa: BLE001
            record_gap(
                gap_logger,
                "jcl",
                source_path or artifact.name,
                f"line {physical}: {exc}",
            )

    # Pass 2: attach instream content to the most recent DD that started
    # with ``DD *``.
    _attach_instream(text, artifact)
    return artifact


def _attach_instream(raw: str, artifact: JclArtifact) -> None:
    lines = raw.splitlines()
    in_instream = False
    target: DDStatement | None = None
    flat_dds: list[DDStatement] = [
        dd for step in artifact.steps for dd in step.dd_statements
    ]
    instream_dds = [dd for dd in flat_dds if dd.is_instream]
    iter_dds = iter(instream_dds)
    # Match ``DD *`` followed by EOL, whitespace, or a comma (``DD *,SYMBOLS=...``).
    instream_starter = re.compile(r"\bDD\s+\*(?:\s|,|$)", re.IGNORECASE)
    for raw_line in lines:
        line = _strip_sequence(raw_line)
        if not in_instream:
            if line.startswith("//") and instream_starter.search(line):
                try:
                    target = next(iter_dds)
                except StopIteration:
                    target = None
                in_instream = True
            continue
        # Inside an instream block: end on ``/*`` (delimiter) or any new
        # ``//STATEMENT``, but tolerate ``//*`` continuation comments
        # (some shops embed those inside DSN blocks).
        if line.startswith("/*"):
            in_instream = False
            target = None
            continue
        if line.startswith("//") and not line.startswith("//*"):
            in_instream = False
            target = None
            # Could also be the next ``DD *`` — re-check this line.
            if instream_starter.search(line):
                try:
                    target = next(iter_dds)
                except StopIteration:
                    target = None
                in_instream = True
            continue
        if target is not None:
            target.instream.append(line)

    # Now scan instream for DB2 DSN blocks.
    for step in artifact.steps:
        for dd in step.dd_statements:
            if dd.is_instream and dd.instream:
                blocks = _scan_db2_blocks(dd.instream)
                if blocks:
                    step.db2_systems.extend(blocks)


def parse_jcl_file(path: Path | str, gap_logger: GapLogger | None = None) -> JclArtifact:
    """Convenience that reads from disk and stamps the source path."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return parse_jcl(text, name=p.stem.upper(), source_path=str(p), gap_logger=gap_logger)
