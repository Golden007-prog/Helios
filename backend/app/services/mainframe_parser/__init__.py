"""Mainframe artifact parsers — AST extraction for the Helios corpus.

Every parser in this package emits a structured pydantic AST. None of them
implement detection or rule logic; that work belongs to JJSCAN+, the score
engine, and the ABEND classifier (Bob's stubs in
``app/services/jjscan/``, ``app/services/score.py``, and
``app/services/abend_classifier.py``).

Each module is deliberately narrow:

* :mod:`.jcl`    — JCL JOB / EXEC / DD / JCLLIB / INCLUDE
* :mod:`.proc`   — cataloged procedure (a JCL subset, ``ProcArtifact``)
* :mod:`.cobol`  — COBOL PROGRAM-ID, COPY, CALL, EXEC SQL/CICS, file ops
* :mod:`.pli`    — PL/I PROCEDURE, %INCLUDE, EXEC SQL, FETCH, CALL
* :mod:`.sql_ddl` — DDL CREATE TABLE, indexes, schema diff

Recoverable parse failures are logged to :mod:`.gaps` (writes
``docs/PARSER_GAPS.md``) instead of raising; the seed loader skips the
file and the demo continues.
"""

from app.services.mainframe_parser.cobol import CobolArtifact, parse_cobol
from app.services.mainframe_parser.gaps import GapLogger, record_gap
from app.services.mainframe_parser.jcl import JclArtifact, parse_jcl
from app.services.mainframe_parser.pli import PliArtifact, parse_pli
from app.services.mainframe_parser.proc import ProcArtifact, parse_proc
from app.services.mainframe_parser.sql_ddl import (
    SchemaDiff,
    TableDef,
    diff_tables,
    parse_ddl,
)

__all__ = [
    "CobolArtifact",
    "GapLogger",
    "JclArtifact",
    "PliArtifact",
    "ProcArtifact",
    "SchemaDiff",
    "TableDef",
    "diff_tables",
    "parse_cobol",
    "parse_ddl",
    "parse_jcl",
    "parse_pli",
    "parse_proc",
    "record_gap",
]
