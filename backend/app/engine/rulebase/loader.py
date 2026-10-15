"""Reads the transcribed CSV tables and their provenance headers.

Each table carries a header block of ``#`` comment lines naming the document, version,
section and page it came from, plus ``verified: true|false``. A table that is missing a
required header field, or that has a malformed row, raises — it is never read partially,
because a half-read regulatory table is worse than no table.

``verified: false`` is not an error. It is the normal state until the owner supplies the
official document, and it propagates into every determination's ``warnings`` and into
the verdict UI as an UNVERIFIED banner.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

RULEBASE_ROOT = Path(__file__).resolve().parent
TABLES_DIRNAME = "tables"

REQUIRED_HEADER_FIELDS = ("table", "document", "version", "section")
#: Cells with this value mean "any"; the rules treat them as a wildcard, never as data.
WILDCARD = "*"


class RulebaseError(RuntimeError):
    """A table is malformed. Always fatal: the engine will not run on a partial table."""


@dataclass(frozen=True, slots=True)
class Table:
    """One transcribed table: its provenance, its notes and its rows."""

    name: str
    path: Path
    document: str
    version: str
    section: str
    page: int | None
    url: str | None
    verified: bool
    notes: tuple[str, ...]
    fieldnames: tuple[str, ...]
    rows: tuple[dict[str, str], ...]

    @property
    def citation_section(self) -> str:
        return self.section

    def warning(self) -> str | None:
        """The sentence the operator sees when this table fed their determination."""
        if self.verified:
            return None
        return (
            f"UNVERIFIED: {self.name} is transcribed from a seed, not from "
            f"{self.document} ({self.section}). This determination must not be submitted "
            f"to an authority until the table is verified."
        )


#: A header line is ``# key: value`` where the key is a bare lowercase identifier. Any
#: other ``#`` line continues the note above it, so a note can wrap across lines and
#: still contain colons ("the 1:1 rule") without being mistaken for a new key.
_HEADER_KEY = re.compile(r"^#\s*([a-z][a-z0-9_]*)\s*:\s*(.*)$")


def _parse_header(lines: list[str], path: Path) -> tuple[dict[str, str], list[str]]:
    meta: dict[str, str] = {}
    notes: list[str] = []
    last_note: int | None = None
    for raw in lines:
        if not raw.lstrip("#").strip():
            continue
        match = _HEADER_KEY.match(raw)
        if match is None:
            if last_note is None:
                raise RulebaseError(
                    f"{path.name}: header line is neither 'key: value' nor a continuation "
                    f"of a note — {raw.strip()!r}"
                )
            notes[last_note] = f"{notes[last_note]} {raw.lstrip('#').strip()}"
            continue
        key, value = match.group(1), match.group(2).strip()
        if key == "note":
            notes.append(value)
            last_note = len(notes) - 1
        else:
            meta[key] = value
            last_note = None
    missing = [f for f in REQUIRED_HEADER_FIELDS if not meta.get(f)]
    if missing:
        raise RulebaseError(f"{path.name}: header is missing {', '.join(missing)}")
    if meta.get("verified") not in {"true", "false"}:
        raise RulebaseError(f"{path.name}: header needs 'verified: true' or 'verified: false'")
    return meta, notes


def load_table(path: Path) -> Table:
    text = path.read_text(encoding="utf-8")
    header_lines = [ln for ln in text.splitlines() if ln.lstrip().startswith("#")]
    body = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    meta, notes = _parse_header(header_lines, path)

    reader = csv.DictReader(body.splitlines())
    if not reader.fieldnames:
        raise RulebaseError(f"{path.name}: no column header row")
    rows: list[dict[str, str]] = []
    for lineno, row in enumerate(reader, start=2):
        if row.get(reader.fieldnames[0]) is None:
            raise RulebaseError(f"{path.name}: row {lineno} is empty")
        # DictReader reports EXTRA columns under a None key and MISSING ones as None
        # values. Both are malformed; neither may be read partially, because a truncated
        # regulatory row is worse than no row.
        if None in row:
            extra = row[None]
            raise RulebaseError(
                f"{path.name}: row {lineno} has more columns than the header "
                f"(trailing: {extra!r}). An unquoted comma in a field will do this."
            )
        if any(v is None for v in row.values()):
            raise RulebaseError(f"{path.name}: row {lineno} has fewer columns than the header")
        rows.append({k: (v or "").strip() for k, v in row.items()})
    if not rows:
        raise RulebaseError(f"{path.name}: no data rows")

    page = meta.get("page", "")
    return Table(
        name=meta["table"],
        path=path,
        document=meta["document"],
        version=meta["version"],
        section=meta["section"],
        page=int(page) if page.isdigit() else None,
        url=meta.get("url") or None,
        verified=meta["verified"] == "true",
        notes=tuple(notes),
        fieldnames=tuple(reader.fieldnames),
        rows=tuple(rows),
    )


@lru_cache
def load_rulebase(version_dir: str = "sora_2_5") -> dict[str, Table]:
    """Every table in a rulebase version, keyed by table name."""
    root = RULEBASE_ROOT / version_dir / TABLES_DIRNAME
    if not root.is_dir():
        raise RulebaseError(f"no tables directory at {root}")
    tables: dict[str, Table] = {}
    for path in sorted(root.glob("*.csv")):
        table = load_table(path)
        if table.name in tables:
            raise RulebaseError(f"two tables both named {table.name!r}")
        tables[table.name] = table
    if not tables:
        raise RulebaseError(f"no CSV tables found in {root}")
    return tables


def rulebase_version(version_dir: str = "sora_2_5") -> str:
    return (RULEBASE_ROOT / version_dir / "VERSION").read_text(encoding="utf-8").strip()


def unverified_tables(version_dir: str = "sora_2_5") -> list[str]:
    return sorted(name for name, t in load_rulebase(version_dir).items() if not t.verified)


def warnings_for(table_names: list[str], version_dir: str = "sora_2_5") -> list[str]:
    """The UNVERIFIED warnings for the tables a determination actually read."""
    tables = load_rulebase(version_dir)
    out = []
    for name in table_names:
        table = tables.get(name)
        if table is None:
            raise RulebaseError(f"unknown table {name!r}")
        if (w := table.warning()) is not None:
            out.append(w)
    return out
