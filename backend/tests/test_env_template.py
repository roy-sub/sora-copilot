"""The environment template and its reference cannot drift from the code.

A setting that exists in `Settings` but not in `.env.example` is a setting nobody will
ever set: the template is what an operator copies. And a variable in the template that
is not in the reference document is one nobody can look up. Both are the kind of gap
that is invisible until a deployment is already half-broken, so they are checked here
rather than remembered.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.config import Settings

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE = ROOT / ".env.example"
REFERENCE = ROOT / "docs" / "ENV Example.md"

#: `KEY=` at the start of a line, which is what a shell would read.
_ASSIGNMENT = re.compile(r"^([A-Z][A-Z0-9_]*)=", re.MULTILINE)


def template_text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def template_keys() -> set[str]:
    return set(_ASSIGNMENT.findall(template_text()))


def test_the_template_exists_and_is_not_empty() -> None:
    """A vacuous pass would be worse than a failure."""
    assert TEMPLATE.is_file(), f"expected the template at {TEMPLATE}"
    assert len(template_keys()) > 10, "suspiciously few variables; is the regex still right?"


def test_every_setting_appears_in_the_template() -> None:
    keys = template_keys()
    missing = sorted(name.upper() for name in Settings.model_fields if name.upper() not in keys)
    assert not missing, (
        "These settings exist in app/config.py but not in .env.example, so nobody "
        f"copying the template would know to set them: {missing}"
    )


def test_the_template_holds_no_setting_the_code_does_not_read() -> None:
    """A variable nobody reads is a variable somebody will set and then wonder about.

    "The code" is wider than `Settings`: `DATABASE_URL` is read by
    `scripts/migrate.py` and deliberately not by the running backend, which talks to
    Supabase over PostgREST and never opens a Postgres socket. So the template is
    checked against the settings *and* the scripts, rather than against a hand-kept
    allow-list that would go stale the first time a script is added.
    """
    known = {name.upper() for name in Settings.model_fields}
    scripts = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (Path(__file__).resolve().parent.parent / "scripts").glob("*.py")
    )
    extra = sorted(
        k
        for k in template_keys()
        if k not in known
        # The frontend's own variables are in the same file by design: one template.
        and not k.startswith("NEXT_PUBLIC_")
        and f'"{k}"' not in scripts
    )
    assert not extra, (
        ".env.example sets variables neither app/config.py nor backend/scripts/ reads: "
        f"{extra}"
    )


def test_no_secret_is_prefixed_public() -> None:
    """`NEXT_PUBLIC_*` is compiled into the browser bundle. A secret must never be one."""
    offenders = [
        k
        for k in template_keys()
        if k.startswith("NEXT_PUBLIC_")
        and any(word in k for word in ("SERVICE_ROLE", "SECRET", "PRIVATE"))
    ]
    assert not offenders, f"these would be published to every visitor: {offenders}"


def test_the_template_ships_no_real_values() -> None:
    """Every value is a placeholder or a safe local default, never a credential."""
    live = re.findall(
        r"^[A-Z][A-Z0-9_]*=(sk-[A-Za-z0-9_-]{8,}|sk_live[A-Za-z0-9_-]*|whsec_[A-Za-z0-9]{8,}|eyJ[A-Za-z0-9_-]{8,})",
        template_text(),
        re.MULTILINE,
    )
    assert not live, f".env.example appears to contain a real credential: {live}"


@pytest.mark.parametrize("key", sorted(template_keys()))
def test_every_template_variable_is_documented(key: str) -> None:
    """Each variable is named in docs/ENV Example.md, which is the reference people read."""
    assert REFERENCE.is_file(), f"expected the reference at {REFERENCE}"
    assert f"`{key}`" in REFERENCE.read_text(encoding="utf-8"), (
        f"{key} is in .env.example but not documented in {REFERENCE.name}"
    )
