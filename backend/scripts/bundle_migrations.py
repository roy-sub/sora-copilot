#!/usr/bin/env python3
"""Concatenate the migrations into one file to paste into the Supabase SQL editor.

`make migrate` is the better route when you have the Postgres connection string. This
exists for the other case: the SQL editor is already open, and five files pasted in
order is five chances to paste one twice or skip one.

The bundle is **not** a second source of truth. It is generated from the same .sql
files, in the same order, and `tests/test_migrations.py` fails if the committed bundle
does not match what this script produces — so a new migration cannot be added and the
bundle forgotten.

Two things it adds that a hand-paste would not:

* The migration ledger, with every bundled file recorded as applied, so a later
  `make migrate` reports "nothing to do" instead of running the whole set again. The
  SQL editor leaves no record of what was pasted; this is what makes the two routes
  agree.
* `begin` / `commit` around the whole thing, so a bundle that fails anywhere leaves
  the database exactly as it was rather than partly built.

    make bundle          # regenerate app/db/migrations/bundle.sql
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "app" / "db" / "migrations"
BUNDLE = MIGRATIONS / "bundle.sql"

HEADER = """\
-- ---------------------------------------------------------------------------
-- SORA Copilot — the whole schema, in one paste.
--
-- GENERATED FILE. Do not edit: `cd backend && make bundle` rewrites it from
-- app/db/migrations/*.sql, and a test fails if the two disagree.
--
-- Supabase dashboard -> SQL Editor -> New query -> paste this whole file -> Run.
-- It is wrapped in a transaction, so it either lands completely or not at all.
--
-- Safe to run on an empty database, and safe to run again: every create is
-- guarded, and each policy and trigger is dropped if it exists before being
-- created. Verified by running the whole set twice against a Postgres 16.
-- The ledger it writes at the end is what lets a later `make migrate` see that
-- these files have already been applied.
--
-- Bundled, in order:
{listing}
-- ---------------------------------------------------------------------------

begin;

"""

LEDGER = """

-- ---------------------------------------------------------------------------
-- The migration ledger.
--
-- `scripts/migrate.py` keeps this table so that re-running is a no-op. Pasting
-- the bundle has applied the same files, so they are recorded here too and the
-- two routes agree about what has run. RLS is enabled and forced with no
-- policy, because 001 establishes that for every table in `public` and a
-- bookkeeping table is not an excuse to break it; the backend holds the
-- service-role key and bypasses RLS.
-- ---------------------------------------------------------------------------

create table if not exists public.schema_migrations (
  filename   text primary key,
  sha256     text not null,
  applied_at timestamptz not null default now()
);
alter table public.schema_migrations enable row level security;
alter table public.schema_migrations force row level security;

insert into public.schema_migrations (filename, sha256) values
{rows}
on conflict (filename) do nothing;

commit;
"""


#: The same rule the runner applies, so the two cannot disagree about what a migration
#: is — including about this file's own output.
MIGRATION_NAME = re.compile(r"^(\d+)_[a-z0-9_]+\.sql$")


def files() -> list[Path]:
    found = [p for p in MIGRATIONS.glob("*.sql") if MIGRATION_NAME.match(p.name)]
    if not found:
        raise SystemExit(f"No NNN_name.sql migrations in {MIGRATIONS}")
    return sorted(found, key=lambda p: (int(MIGRATION_NAME.match(p.name).group(1)), p.name))  # type: ignore[union-attr]


def build() -> str:
    paths = files()
    listing = "\n".join(f"--   {p.name}" for p in paths)
    parts = [HEADER.format(listing=listing)]
    for path in paths:
        parts.append(
            f"-- ===========================================================================\n"
            f"-- {path.name}\n"
            f"-- ===========================================================================\n\n"
        )
        parts.append(path.read_text(encoding="utf-8").rstrip() + "\n\n")
    rows = ",\n".join(
        f"  ('{p.name}', '{hashlib.sha256(p.read_bytes()).hexdigest()}')" for p in paths
    )
    parts.append(LEDGER.format(rows=rows))
    return "".join(parts)


if __name__ == "__main__":
    BUNDLE.write_text(build(), encoding="utf-8")
    print(f"Wrote {BUNDLE.relative_to(ROOT.parent)} — {len(files())} migrations, "
          f"{len(BUNDLE.read_text(encoding='utf-8').splitlines())} lines.")
