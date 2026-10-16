#!/usr/bin/env python3
"""Apply the SQL migrations to a Postgres database — usually a Supabase project.

Supabase does not create this schema for you. Signing up gives you an empty database
with Supabase's own `auth` and `storage` schemas in it; every table this product reads
and writes is in `app/db/migrations/`, and something has to run them. Until now that
something was a human pasting five files into the SQL editor in the right order, which
is a step that gets half-done.

    make migrate            # apply whatever has not been applied
    make migrate-status     # say what would run, change nothing

What it does, and why each part is there:

* **A ledger.** `public.schema_migrations` records every file applied, with the SHA-256
  of the text that was applied. Re-running is then a no-op rather than an error — which
  matters because Postgres has no `CREATE POLICY IF NOT EXISTS`, so replaying `001`
  over a live database fails halfway through and leaves it part-migrated.
* **One transaction per file.** A migration that fails rolls back whole. There is no
  state where half of `002` is in the database.
* **A changed-file warning.** If a file's hash no longer matches what was applied, it
  says so and stops. Editing an applied migration is the one thing the migrations
  README forbids, and this is where that rule gets enforced rather than remembered.
* **`--baseline`.** For a database where the SQL was already pasted in by hand: records
  the files as applied without running them, so the ledger starts telling the truth.

It never drops anything and never rewrites a migration.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "app" / "db" / "migrations"
LEDGER = "public.schema_migrations"

# RLS enabled and forced, with no policy, because 001 establishes that invariant for
# every table in `public` and a bookkeeping table is not an excuse to break it. The
# backend holds the service-role key and bypasses RLS; nothing else should read this.
CREATE_LEDGER = f"""
create table if not exists {LEDGER} (
  filename   text primary key,
  sha256     text not null,
  applied_at timestamptz not null default now()
);
alter table {LEDGER} enable row level security;
alter table {LEDGER} force row level security;
"""


def _load_env_file(path: Path) -> None:
    """Read KEY=VALUE lines from a .env the same way the app does.

    Values already in the environment win, so `DATABASE_URL=... make migrate` overrides
    the file without editing it.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def database_url() -> str:
    for candidate in (ROOT / ".env", ROOT.parent / ".env"):
        _load_env_file(candidate)
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    sys.exit(
        "DATABASE_URL is not set.\n"
        "\n"
        "This is the Postgres connection string, which is NOT the same thing as\n"
        "SUPABASE_URL. In the Supabase dashboard: Connect (top of the page) →\n"
        "Session pooler → copy the URI, and put your database password in it.\n"
        "\n"
        "Then add it to backend/.env as:\n"
        "  DATABASE_URL=postgresql://postgres.<ref>:<password>@<host>:5432/postgres\n"
        "\n"
        "Use the session pooler (port 5432) or the direct connection, not the\n"
        "transaction pooler on 6543 — that one cannot run schema changes."
    )


def _psycopg():
    try:
        import psycopg
    except ModuleNotFoundError:
        sys.exit(
            "psycopg is not installed. It ships in the dev extra, which is what\n"
            "`make install` installs:\n"
            "\n"
            "  cd backend && make install\n"
            "\n"
            "or, directly:  .venv/bin/pip install 'psycopg[binary]'"
        )
    return psycopg


def files() -> list[Path]:
    found = sorted(MIGRATIONS.glob("*.sql"))
    if not found:
        sys.exit(f"No .sql files in {MIGRATIONS}")
    # Numeric order, not string order, so 010 lands after 009 rather than after 001.
    return sorted(found, key=lambda p: (int(re.match(r"(\d+)", p.name).group(1)), p.name))  # type: ignore[union-attr]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Say what would run; change nothing.")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Record every migration as applied WITHOUT running it, for a database "
        "whose schema was already created by hand.",
    )
    args = parser.parse_args()

    psycopg = _psycopg()
    url = database_url()
    where = re.sub(r"//[^@]*@", "//<credentials>@", url)

    pending: list[Path] = []
    with psycopg.connect(url, autocommit=True) as conn:
        print(f"Database  {where}")
        conn.execute(CREATE_LEDGER)
        applied = {
            row[0]: row[1]
            for row in conn.execute(f"select filename, sha256 from {LEDGER}").fetchall()
        }

        for path in files():
            sha = digest(path)
            if path.name in applied:
                if applied[path.name] != sha:
                    print(f"  CHANGED   {path.name}")
                    sys.exit(
                        f"\n{path.name} has been edited since it was applied.\n"
                        "A migration that has run is never edited — the database cannot be\n"
                        "rebuilt by replaying it any more. Revert the file and add the\n"
                        "correction as the next numbered migration instead."
                    )
                print(f"  applied   {path.name}")
                continue
            pending.append(path)
            print(f"  PENDING   {path.name}")

        if not pending:
            print("\nNothing to do: the database is up to date.")
            return 0

        if args.dry_run:
            print(f"\n{len(pending)} migration(s) would run. Nothing was changed.")
            return 0

        for path in pending:
            sha = digest(path)
            if args.baseline:
                conn.execute(
                    f"insert into {LEDGER} (filename, sha256) values (%s, %s)", (path.name, sha)
                )
                print(f"  baseline  {path.name}  (recorded, not run)")
                continue
            print(f"  running   {path.name} …", end="", flush=True)
            # One transaction per file: a migration either lands whole or not at all.
            with psycopg.connect(url) as tx:
                tx.execute(path.read_text(encoding="utf-8"))
                tx.execute(
                    f"insert into {LEDGER} (filename, sha256) values (%s, %s)", (path.name, sha)
                )
                tx.commit()
            print(" done")

    verb = "recorded" if args.baseline else "applied"
    print(f"\n{len(pending)} migration(s) {verb}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
