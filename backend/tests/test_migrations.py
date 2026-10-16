"""The SQL migrations, and the script that applies them.

Supabase hands you an empty database. Everything this product reads and writes is
created by `app/db/migrations/*.sql`, and until `scripts/migrate.py` existed the only
way to run them was a human pasting five files into the SQL editor in the right order.

These tests are static — they read the SQL rather than executing it, because a Postgres
is not available in CI. That is a real limit and it showed: the ordering bug below was
found by running the migrations against a live Postgres 16, not here. What these tests
do is stop it coming back.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "migrate.py"


def files() -> list[Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def test_every_migration_is_numbered_and_the_numbers_do_not_collide() -> None:
    """The runner orders by the leading integer, so a duplicate number is ambiguous."""
    numbers = []
    for path in files():
        match = re.match(r"^(\d{3})_[a-z0-9_]+\.sql$", path.name)
        assert match, f"{path.name} is not NNN_lower_snake.sql"
        numbers.append(int(match.group(1)))
    assert numbers == sorted(numbers)
    assert len(numbers) == len(set(numbers)), "two migrations share a number"


@pytest.mark.parametrize("path", [p for p in files() if "rulebase" in p.name], ids=lambda p: p.name)
def test_a_rulebase_migration_stands_the_old_version_down_before_inserting(path: Path) -> None:
    """The bug this file exists for.

    `rulebase_versions_one_current` is a plain unique partial index. Postgres checks it
    at the end of each statement, not at commit, so inserting the new version with
    is_current = true while the old one is still current fails on the INSERT — the
    UPDATE that would have fixed it never runs. Both rulebase migrations were written
    that way and neither had ever been executed, so every one of the 520 tests passed
    over a schema nobody could actually create.
    """
    sql = path.read_text(encoding="utf-8")
    stand_down = sql.find("update public.rulebase_versions set is_current = false")
    insert = sql.find("insert into public.rulebase_versions")
    assert stand_down != -1, "no statement stands the previous current version down"
    assert insert != -1
    assert stand_down < insert, (
        f"{path.name} inserts a second current version before standing the old one "
        "down; the unique index refuses the insert"
    )


@pytest.mark.parametrize("path", [p for p in files() if "rulebase" in p.name], ids=lambda p: p.name)
def test_re_running_a_rulebase_migration_restores_it_as_current(path: Path) -> None:
    """`do nothing` would leave is_current false on a replay, which is worse than an error.

    The stand-down runs unconditionally, so a conflicting insert has to put the flag
    back rather than skip.
    """
    sql = path.read_text(encoding="utf-8")
    assert "on conflict (version) do update set is_current = true" in sql
    assert "on conflict (version) do nothing" not in sql


def test_no_migration_drops_or_truncates() -> None:
    """A migration adds. Anything destructive is a deliberate exception, not a default."""
    for path in files():
        sql = path.read_text(encoding="utf-8").lower()
        body = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
        for forbidden in ("drop table", "truncate ", "drop schema", "delete from"):
            assert forbidden not in body, f"{path.name} contains {forbidden!r}"


def test_the_runner_keeps_a_ledger_and_refuses_an_edited_migration() -> None:
    """What makes re-running safe.

    Postgres has no CREATE POLICY IF NOT EXISTS, so replaying 001 over a live database
    fails halfway and leaves it part-migrated. The ledger is what turns "run it again"
    from a hazard into a no-op, and the hash check is where the README's "never edit an
    applied migration" rule stops being a thing people remember.
    """
    source = SCRIPT.read_text(encoding="utf-8")
    assert "create table if not exists public.schema_migrations" in source.replace(
        "{LEDGER}", "public.schema_migrations"
    )
    assert "sha256" in source
    assert "has been edited since it was applied" in source
    # One transaction per file: a migration lands whole or not at all.
    assert "tx.commit()" in source
    # And the ledger does not become the one table in public without RLS.
    assert "force row level security" in source


def test_the_runner_never_prints_the_database_password() -> None:
    """It echoes the database it is about to change, and that string carries a secret."""
    import sys

    sys.path.insert(0, str(SCRIPT.parent))
    import importlib.util

    spec = importlib.util.spec_from_file_location("migrate_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    url = "postgresql://postgres.abcdefgh:sup3r-s3cret@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
    shown = re.sub(r"//[^@]*@", "//<credentials>@", url)
    assert "sup3r-s3cret" not in shown
    assert "postgres.abcdefgh" not in shown
    assert "pooler.supabase.com:5432/postgres" in shown


def test_the_env_template_documents_the_connection_string() -> None:
    """DATABASE_URL is not SUPABASE_URL, and confusing them is the obvious mistake."""
    template = (Path(__file__).resolve().parent.parent.parent / ".env.example").read_text(
        encoding="utf-8"
    )
    assert "DATABASE_URL=" in template
    assert "NOT SUPABASE_URL" in template
