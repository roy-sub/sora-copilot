"""The neurosymbolic boundary, enforced.

The product's claim is that the language model never computes a determination. These
tests are what makes that a fact about the codebase rather than a promise in a README.
They walk the AST of real source files, so they fail on an import that is merely
*present*, even if it is never called.

Build spec §4. Narrative in docs/ARCHITECTURE.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
ENGINE = APP / "engine"
LLM = APP / "services" / "llm.py"

#: Everything app/engine/** may import. Anything else fails the build.
ENGINE_ALLOWED_THIRD_PARTY = {"clingo", "clorm", "z3"}
ENGINE_ALLOWED_INTERNAL_PREFIXES = ("app.domain", "app.engine")
ENGINE_ALLOWED_TYPING = {"pydantic"}

#: Named explicitly so that a new network or persistence dependency cannot slip in under
#: a name the stdlib check happens to tolerate.
ENGINE_FORBIDDEN = {
    "anthropic",
    "httpx",
    "requests",
    "aiohttp",
    "urllib3",
    "supabase",
    "openai",
    "boto3",
    "socket",
    "urllib",
    "http",
    "ftplib",
    "smtplib",
    "telnetlib",
    "subprocess",
}

STDLIB = set(getattr(__import__("sys"), "stdlib_module_names", ()))


def _python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _imports(path: Path) -> list[tuple[str, int]]:
    """Every module an AST imports, as (dotted_root_or_full, lineno)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        # A relative import stays inside the package it is written in, so only
        # absolute ImportFrom nodes can cross the boundary.
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.module, node.lineno))
    return found


def _is_allowed_for_engine(module: str) -> bool:
    root = module.split(".")[0]
    if root in ENGINE_FORBIDDEN:
        return False
    if module.startswith(ENGINE_ALLOWED_INTERNAL_PREFIXES):
        return True
    if root == "app":
        return False  # any other app.* subpackage is off limits
    if root in ENGINE_ALLOWED_THIRD_PARTY or root in ENGINE_ALLOWED_TYPING:
        return True
    return root in STDLIB


def test_engine_package_exists() -> None:
    """A vacuous pass would be worse than a failure, so prove there is something to check."""
    files = _python_files(ENGINE)
    assert files, f"no Python files found under {ENGINE}"


@pytest.mark.parametrize("path", _python_files(ENGINE), ids=lambda p: str(p.relative_to(APP)))
def test_engine_imports_are_pure(path: Path) -> None:
    """app/engine/** may import only stdlib, clingo/clorm/z3, pydantic and app.domain."""
    offenders = [
        f"{path.relative_to(APP)}:{lineno} imports {module!r}"
        for module, lineno in _imports(path)
        if not _is_allowed_for_engine(module)
    ]
    assert not offenders, "The rules engine must stay pure — no network, no LLM, no database.\n" + "\n".join(
        offenders
    )


def test_llm_module_exists() -> None:
    assert LLM.is_file(), f"expected the LLM boundary module at {LLM}"


def test_llm_cannot_reach_the_engine() -> None:
    """services/llm.py has no import path to anything that computes a determination."""
    offenders = [
        f"line {lineno}: {module!r}"
        for module, lineno in _imports(LLM)
        if module.startswith(("app.engine", "app.db", "app.services.determination"))
    ]
    assert not offenders, (
        "services/llm.py must not be able to reach the engine, the database or the "
        "determination service.\n" + "\n".join(offenders)
    )


def _docstring_node_ids(tree: ast.Module) -> set[int]:
    """Identity of every Constant node that is a docstring.

    Compared by identity rather than by value: ``ast.get_docstring`` returns the cleaned
    text while the node holds the raw literal, so the two never compare equal.
    """
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = getattr(node, "body", [])
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            ids.add(id(body[0].value))
    return ids


def test_llm_module_does_not_write_determinations() -> None:
    """The module that calls Anthropic never names the determinations table in code.

    Docstrings may discuss it — that is how the rule gets documented in the place it
    applies. Only string literals that are actually executable are checked.
    """
    tree = ast.parse(LLM.read_text(encoding="utf-8"))
    docstrings = _docstring_node_ids(tree)
    offenders = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and "determinations" in node.value
    ]
    assert not offenders, f"services/llm.py references the determinations table in code: {offenders}"


def test_the_docstring_filter_does_not_make_the_check_vacuous() -> None:
    """Guard the guard: a non-docstring literal naming the table must be caught."""
    tree = ast.parse('"""Doc mentioning determinations."""\nTABLE = "determinations"\n')
    docstrings = _docstring_node_ids(tree)
    caught = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and id(n) not in docstrings
        and "determinations" in n.value
    ]
    assert caught == ["determinations"]


def test_anthropic_is_imported_in_exactly_one_module() -> None:
    """Only services/llm.py may import the Anthropic SDK, anywhere in the app."""
    importers = [
        path.relative_to(APP)
        for path in _python_files(APP)
        if any(module.split(".")[0] == "anthropic" for module, _ in _imports(path))
    ]
    assert importers in ([], [LLM.relative_to(APP)]), (
        f"anthropic may only be imported by services/llm.py; found: {importers}"
    )
