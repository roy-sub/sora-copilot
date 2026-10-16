"""The backend is not only Python, and a wheel that drops its data is silently broken.

The rulebase is CSV and clingo source, the country packs are JSON, the migrations are
SQL and the renderers carry their own typeface. None of those directories is a Python
package, so each has to be declared as package data — and the failure mode if one is
missed is not an ImportError at startup but a 500 the first time somebody runs a
determination.

These tests check the declaration against what is actually on disk, so a new data
directory cannot be added without being shipped.
"""

from __future__ import annotations

import tomllib
from fnmatch import fnmatch
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
PYPROJECT = BACKEND / "pyproject.toml"

#: Every extension the app loads at runtime but Python would not package by itself.
DATA_SUFFIXES = {".lp", ".csv", ".json", ".sql", ".ttf"}

#: Files that exist for people, not for the program.
IGNORED_NAMES = {"openapi.json"}


def patterns() -> list[str]:
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return list(config["tool"]["setuptools"]["package-data"]["app"])


def data_files() -> list[Path]:
    return sorted(
        p
        for p in APP.rglob("*")
        if p.is_file()
        and (p.suffix in DATA_SUFFIXES or p.name == "VERSION")
        and "__pycache__" not in p.parts
        and p.name not in IGNORED_NAMES
    )


def test_there_are_data_files_to_ship() -> None:
    """A vacuous pass would be worse than a failure."""
    found = data_files()
    assert len(found) > 20, f"expected the rulebase and the fonts, found {len(found)}"


@pytest.mark.parametrize("path", data_files(), ids=lambda p: str(p.relative_to(APP)))
def test_every_runtime_data_file_is_declared_as_package_data(path: Path) -> None:
    relative = str(path.relative_to(APP))
    assert any(fnmatch(relative, pattern) for pattern in patterns()), (
        f"{relative} is loaded at runtime but no package-data pattern in pyproject.toml "
        "matches it, so `pip install .` would produce a backend without it."
    )


def test_the_bundled_typeface_is_present_and_usable() -> None:
    """The renderers do not fall back to a core font; they would drop half the glyphs."""
    from app.services import fonts

    for path in (fonts.regular(), fonts.bold()):
        assert path.is_file()
        assert path.stat().st_size > 100_000, f"{path.name} looks truncated"
    assert (fonts.FONT_DIR / "LICENSE.DejaVu.txt").is_file(), (
        "the typeface is redistributed, so its licence ships with it"
    )


def test_nothing_still_depends_on_docker_or_weasyprint() -> None:
    """Both were removed together: the native libraries only existed in the image."""
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    declared = " ".join(config["project"]["dependencies"]).lower()
    assert "weasyprint" not in declared
    assert not (BACKEND / "Dockerfile").exists()
    assert not (BACKEND / ".dockerignore").exists()


def test_the_entry_point_runs_without_a_process_manager() -> None:
    """`python main.py` is the documented way to start it, so it has to parse."""
    import main

    args = main.parse_args([])
    assert args.port == 8000
    assert main.parse_args(["--port", "9000"]).port == 9000
    assert main.parse_args(["--prod"]).prod is True


def test_the_minimum_python_matches_what_pyproject_declares() -> None:
    """Two places say 3.12 and they have to agree, or the guard lies to someone."""
    import main

    config = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    declared = config["project"]["requires-python"]
    assert declared.startswith(">=")
    assert tuple(int(n) for n in declared[2:].split(".")) == main.MIN_PYTHON


def test_too_old_a_python_says_so_instead_of_blaming_uvicorn(capsys, monkeypatch) -> None:
    """The failure a 3.11 user actually hits, and the message they actually need.

    pip refuses the install with "requires a different Python" and installs *nothing*,
    so the next thing they see is `uvicorn is not installed` — which sends them to redo
    the install that already failed. The version check has to come first and name the
    real cause.
    """
    import main

    monkeypatch.setattr(main, "MIN_PYTHON", (99, 0))
    assert main.main([]) == 1
    err = capsys.readouterr().err
    assert "needs 99.0 or newer" in err
    assert "installed nothing" in err
    assert "uvicorn" not in err.lower()
