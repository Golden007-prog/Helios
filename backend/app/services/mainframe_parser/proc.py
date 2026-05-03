"""Cataloged procedure parser.

A PROC is a JCL subset: a leading ``//NAME PROC param=default,...`` card,
zero or more steps, optionally a trailing ``//NAME PEND``. The JCL parser
already does most of the work; this module wraps the result in a
:class:`ProcArtifact` so the corpus seeder can put it in
``helios_proc_artifacts`` with first-class parameter metadata.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.services.mainframe_parser.gaps import GapLogger
from app.services.mainframe_parser.jcl import Step, parse_jcl


class ProcArtifact(BaseModel):
    """Subtype of :class:`JclArtifact` exposing PROC-specific metadata."""

    model_config = ConfigDict(extra="allow")
    name: str
    parameters: dict[str, str | None] = Field(default_factory=dict)
    steps: list[Step] = Field(default_factory=list)
    pgm_refs: list[str] = Field(default_factory=list)
    proc_refs: list[str] = Field(default_factory=list)
    steplib_dsns: list[str] = Field(default_factory=list)
    library_id: str | None = None
    member: str | None = None


def parse_proc(
    text: str,
    *,
    name: str | None = None,
    library_id: str | None = None,
    source_path: str | None = None,
    gap_logger: GapLogger | None = None,
) -> ProcArtifact:
    """Parse a cataloged proc into a :class:`ProcArtifact`."""

    base = parse_jcl(
        text,
        name=name,
        source_path=source_path,
        gap_logger=gap_logger,
    )
    member = name or base.name
    return ProcArtifact(
        name=base.name,
        parameters=base.proc_parameters,
        steps=base.steps,
        pgm_refs=base.pgm_refs,
        proc_refs=base.proc_refs,
        steplib_dsns=base.steplib_dsns,
        library_id=library_id,
        member=member,
    )


def parse_proc_file(
    path: Path | str,
    *,
    library_id: str | None = None,
    gap_logger: GapLogger | None = None,
) -> ProcArtifact:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return parse_proc(
        text,
        name=p.stem.upper(),
        library_id=library_id,
        source_path=str(p),
        gap_logger=gap_logger,
    )
