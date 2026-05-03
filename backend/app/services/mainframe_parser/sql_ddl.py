"""SQL DDL parser — DB2 / XDB dialect-aware.

Extracts CREATE TABLE definitions (column list with types, lengths,
nullability, defaults), PRIMARY KEY, FOREIGN KEY, CREATE INDEX, and the
``IN DATABASE``/``IN tablespace`` / ``AUDIT`` / ``DATA CAPTURE`` clauses
that distinguish the DB2 and XDB DDL we ship in the corpus.

The :func:`diff_tables` function compares two :class:`TableDef` instances
and returns a structured :class:`SchemaDiff` — used by the Region Atlas
DDL diff feature and by the ``corpus_diff_schema`` MCP tool.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.mainframe_parser.gaps import GapLogger, record_gap


class ColumnDef(BaseModel):
    name: str
    type: str
    length: int | None = None
    precision: int | None = None
    scale: int | None = None
    nullable: bool = True
    default_clause: str | None = None
    raw: str = ""


class IndexDef(BaseModel):
    name: str
    table: str
    columns: list[str] = Field(default_factory=list)
    unique: bool = False


class ForeignKeyDef(BaseModel):
    name: str | None = None
    columns: list[str] = Field(default_factory=list)
    references_table: str = ""
    references_columns: list[str] = Field(default_factory=list)


class TableDef(BaseModel):
    """One ``CREATE TABLE`` statement and the indexes/constraints around it."""

    model_config = ConfigDict(extra="allow")
    name: str
    schema_name: str | None = None
    dialect: Literal["db2", "xdb", "unknown"] = "unknown"
    columns: list[ColumnDef] = Field(default_factory=list)
    primary_key: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKeyDef] = Field(default_factory=list)
    indexes: list[IndexDef] = Field(default_factory=list)
    tablespace: str | None = None
    in_database: str | None = None
    audit: str | None = None
    data_capture: str | None = None


class ColumnDiff(BaseModel):
    column: str
    field: str
    a: str | int | bool | None
    b: str | int | bool | None


class SchemaDiff(BaseModel):
    """Field-level diff between two :class:`TableDef` instances."""

    table: str
    dialect_a: str
    dialect_b: str
    only_in_a: list[str] = Field(default_factory=list)
    only_in_b: list[str] = Field(default_factory=list)
    column_diffs: list[ColumnDiff] = Field(default_factory=list)
    pk_diff: tuple[list[str], list[str]] | None = None
    tablespace_diff: tuple[str | None, str | None] | None = None
    in_database_diff: tuple[str | None, str | None] | None = None
    audit_diff: tuple[str | None, str | None] | None = None


# ---------------------------------------------------------------------------
# Pre-parsing helpers
# ---------------------------------------------------------------------------


_COMMENT_RE = re.compile(r"--[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_comments(text: str) -> str:
    text = _BLOCK_COMMENT_RE.sub(" ", text)
    text = _COMMENT_RE.sub(" ", text)
    return text


def _split_statements(text: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    in_quote = False
    for ch in text:
        if ch == "'":
            in_quote = not in_quote
            buf.append(ch)
            continue
        if ch == ";" and not in_quote:
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


# ---------------------------------------------------------------------------
# Statement parsers
# ---------------------------------------------------------------------------


_CREATE_TABLE_RE = re.compile(
    r"\bCREATE\s+TABLE\s+(?:(?P<schema>[A-Z][A-Z0-9_]*)\.)?"
    r"(?P<name>[A-Z][A-Z0-9_]*)\s*\((?P<body>.*?)\)\s*"
    r"(?P<trailing>(?:[A-Z\s\d.()'_/-]*))?$",
    re.IGNORECASE | re.DOTALL,
)
_CREATE_INDEX_RE = re.compile(
    r"\bCREATE\s+(?P<unique>UNIQUE\s+)?INDEX\s+(?P<idx>[A-Z][A-Z0-9_]*)\s+ON\s+"
    r"(?:(?P<schema>[A-Z][A-Z0-9_]*)\.)?(?P<table>[A-Z][A-Z0-9_]*)\s*\((?P<cols>[^)]+)\)",
    re.IGNORECASE | re.DOTALL,
)
_PK_RE = re.compile(r"\bPRIMARY\s+KEY\s*\(([^)]+)\)", re.IGNORECASE)
_FK_RE = re.compile(
    r"\bFOREIGN\s+KEY\s+(?P<name>[A-Z][A-Z0-9_]*)?\s*\((?P<cols>[^)]+)\)\s*"
    r"REFERENCES\s+(?P<ref_table>[A-Z][A-Z0-9_]*)\s*\((?P<ref_cols>[^)]+)\)",
    re.IGNORECASE | re.DOTALL,
)
_TYPE_RE = re.compile(
    r"^(?P<type>[A-Z][A-Z0-9_]*)"
    r"(?:\(\s*(?P<a>\d+)(?:\s*,\s*(?P<b>\d+))?\s*\))?",
    re.IGNORECASE,
)


def _parse_columns_and_constraints(
    body: str,
) -> tuple[list[ColumnDef], list[str], list[ForeignKeyDef]]:
    """Split a ``CREATE TABLE`` body into columns and constraints.

    Top-level commas split entries; inside a single entry parens are kept
    intact (e.g., ``DECIMAL(9,2)``).
    """
    entries: list[str] = []
    buf: list[str] = []
    depth = 0
    in_quote = False
    for ch in body:
        if ch == "'":
            in_quote = not in_quote
        if not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                entry = "".join(buf).strip()
                if entry:
                    entries.append(entry)
                buf = []
                continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        entries.append(tail)

    columns: list[ColumnDef] = []
    pk: list[str] = []
    fks: list[ForeignKeyDef] = []

    for entry in entries:
        upper = entry.upper().lstrip()
        if upper.startswith("PRIMARY KEY"):
            m = _PK_RE.search(entry)
            if m:
                pk = [c.strip().upper() for c in m.group(1).split(",")]
            continue
        if upper.startswith("FOREIGN KEY"):
            m = _FK_RE.search(entry)
            if m:
                fks.append(
                    ForeignKeyDef(
                        name=m.group("name").upper() if m.group("name") else None,
                        columns=[c.strip().upper() for c in m.group("cols").split(",")],
                        references_table=m.group("ref_table").upper(),
                        references_columns=[
                            c.strip().upper() for c in m.group("ref_cols").split(",")
                        ],
                    )
                )
            continue
        if upper.startswith(("CONSTRAINT", "UNIQUE", "CHECK")):
            continue
        col = _parse_column(entry)
        if col is not None:
            columns.append(col)

    return columns, pk, fks


def _parse_column(entry: str) -> ColumnDef | None:
    parts = entry.split(None, 1)
    if len(parts) < 2:
        return None
    name = parts[0].strip().upper()
    rest = parts[1].strip()
    type_match = _TYPE_RE.match(rest)
    if not type_match:
        return None
    type_text = type_match.group("type").strip().upper()
    a = type_match.group("a")
    b = type_match.group("b")
    length: int | None = None
    precision: int | None = None
    scale: int | None = None
    if type_text in {"CHAR", "VARCHAR", "VARGRAPHIC"}:
        if a is not None:
            length = int(a)
    elif type_text in {"DECIMAL", "NUMERIC"}:
        if a is not None:
            precision = int(a)
        if b is not None:
            scale = int(b)
    elif a is not None:
        length = int(a)
    upper_rest = rest.upper()
    nullable = "NOT NULL" not in upper_rest
    default_clause: str | None = None
    if "WITH DEFAULT" in upper_rest:
        idx = upper_rest.find("WITH DEFAULT")
        tail = rest[idx + len("WITH DEFAULT") :].strip()
        default_clause = tail or "default"
    elif "DEFAULT" in upper_rest:
        idx = upper_rest.find("DEFAULT")
        default_clause = rest[idx + len("DEFAULT") :].strip()
    return ColumnDef(
        name=name,
        type=type_text,
        length=length,
        precision=precision,
        scale=scale,
        nullable=nullable,
        default_clause=default_clause,
        raw=entry.strip(),
    )


def parse_ddl(
    text: str,
    *,
    dialect: Literal["db2", "xdb", "unknown"] = "unknown",
    source_path: str | None = None,
    gap_logger: GapLogger | None = None,
) -> list[TableDef]:
    """Parse a DDL script into a list of :class:`TableDef`."""

    cleaned = _strip_comments(text)
    statements = _split_statements(cleaned)

    tables: dict[str, TableDef] = {}

    for stmt in statements:
        m = _CREATE_TABLE_RE.search(stmt)
        if m:
            name = m.group("name").upper()
            schema_name = (m.group("schema") or "").upper() or None
            body = m.group("body")
            try:
                columns, pk, fks = _parse_columns_and_constraints(body)
            except Exception as exc:  # noqa: BLE001
                record_gap(gap_logger, "sql_ddl", source_path or name, f"column parse: {exc}")
                continue
            trailing = (m.group("trailing") or "").upper()
            in_database = None
            tablespace = None
            audit = None
            data_capture = None
            in_match = re.search(r"\bIN\s+DATABASE\s+([A-Z0-9_]+)", trailing)
            if in_match:
                in_database = in_match.group(1)
            ts_match = re.search(r"\bIN\s+([A-Z0-9_]+)\.([A-Z0-9_]+)", trailing)
            if ts_match:
                tablespace = f"{ts_match.group(1)}.{ts_match.group(2)}"
            audit_match = re.search(r"\bAUDIT\s+([A-Z]+)", trailing)
            if audit_match:
                audit = audit_match.group(1)
            dc_match = re.search(r"\bDATA\s+CAPTURE\s+([A-Z]+)", trailing)
            if dc_match:
                data_capture = dc_match.group(1)
            table = TableDef(
                name=name,
                schema_name=schema_name,
                dialect=dialect,
                columns=columns,
                primary_key=pk,
                foreign_keys=fks,
                tablespace=tablespace,
                in_database=in_database,
                audit=audit,
                data_capture=data_capture,
            )
            tables[name] = table
            continue
        m = _CREATE_INDEX_RE.search(stmt)
        if m:
            tbl_name = m.group("table").upper()
            idx = IndexDef(
                name=m.group("idx").upper(),
                table=tbl_name,
                columns=[c.strip().upper() for c in m.group("cols").split(",")],
                unique=bool(m.group("unique")),
            )
            target = tables.get(tbl_name)
            if target is not None:
                target.indexes.append(idx)
            continue

    return list(tables.values())


def parse_ddl_file(
    path: Path | str,
    *,
    dialect: Literal["db2", "xdb", "unknown"] = "unknown",
    gap_logger: GapLogger | None = None,
) -> list[TableDef]:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return parse_ddl(text, dialect=dialect, source_path=str(p), gap_logger=gap_logger)


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


def diff_tables(a: TableDef, b: TableDef) -> SchemaDiff:
    """Return a field-level :class:`SchemaDiff` between two table definitions."""

    diff = SchemaDiff(table=a.name, dialect_a=a.dialect, dialect_b=b.dialect)

    a_cols = {c.name: c for c in a.columns}
    b_cols = {c.name: c for c in b.columns}

    diff.only_in_a = sorted(set(a_cols) - set(b_cols))
    diff.only_in_b = sorted(set(b_cols) - set(a_cols))

    common = sorted(set(a_cols) & set(b_cols))
    for name in common:
        ca = a_cols[name]
        cb = b_cols[name]
        for field_name in ("type", "length", "precision", "scale", "nullable", "default_clause"):
            va = getattr(ca, field_name)
            vb = getattr(cb, field_name)
            if va != vb:
                diff.column_diffs.append(
                    ColumnDiff(column=name, field=field_name, a=va, b=vb)
                )

    if a.primary_key != b.primary_key:
        diff.pk_diff = (a.primary_key, b.primary_key)
    if a.tablespace != b.tablespace:
        diff.tablespace_diff = (a.tablespace, b.tablespace)
    if a.in_database != b.in_database:
        diff.in_database_diff = (a.in_database, b.in_database)
    if a.audit != b.audit:
        diff.audit_diff = (a.audit, b.audit)

    return diff
