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

# ------------------------------------------------------------------ transitive reachability


def _module_name(path: Path) -> str:
    """app/services/llm.py → app.services.llm"""
    rel = path.relative_to(BACKEND).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _import_targets(path: Path) -> set[str]:
    """Every app.* module a file imports, resolving submodule imports correctly.

    `from app.services import intake` names the PACKAGE in the AST, but it imports the
    submodule — so both `app.services` and `app.services.intake` are edges. Recording
    only the package is what made an earlier version of this test pass while a two-hop
    path to the database existed.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app"):
                    out.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if not node.module.startswith("app"):
                continue
            out.add(node.module)
            # `from app.x import y` may import the submodule app.x.y or an attribute of
            # app.x. Adding both is safe: a name that is not a module has no edges.
            for alias in node.names:
                out.add(f"{node.module}.{alias.name}")
    return out


def _internal_graph() -> dict[str, set[str]]:
    """Every app.* module and the app.* modules it imports, directly."""
    modules = {_module_name(p) for p in _python_files(APP)}
    graph: dict[str, set[str]] = {}
    for path in _python_files(APP):
        # Keep only edges that are real modules in this codebase; an attribute import
        # resolves to its package, which is already an edge.
        graph[_module_name(path)] = {t for t in _import_targets(path) if t in modules}
    return graph


def _reachable(start: str, graph: dict[str, set[str]]) -> set[str]:
    """Every app.* module reachable from `start`, following imports transitively."""
    seen: set[str] = set()
    stack = [start]
    while stack:
        current = stack.pop()
        for target in graph.get(current, set()):
            if target in seen:
                continue
            seen.add(target)
            stack.append(target)
    return seen


def test_the_import_graph_is_not_empty() -> None:
    graph = _internal_graph()
    assert "app.services.llm" in graph
    assert graph["app.services.llm"], "llm.py imports nothing from app, which is suspicious"


def test_llm_has_no_import_path_to_the_engine_or_the_database() -> None:
    """The build spec says "no import path", which is TRANSITIVE, not just direct.

    A module two hops from the database is still a module that can reach it, so this
    walks the whole graph rather than one file's import list.
    """
    graph = _internal_graph()
    reachable = _reachable("app.services.llm", graph)
    forbidden = sorted(
        m
        for m in reachable
        if m.startswith(("app.engine", "app.db"))
        or m == "app.services.determination"
    )
    assert not forbidden, (
        "services/llm.py can reach these transitively:\n  "
        + "\n  ".join(forbidden)
        + "\nIt reads field metadata from app.domain.fields precisely so it cannot."
    )


def test_the_engine_has_no_import_path_out_of_itself_and_the_domain() -> None:
    """Same check for the engine: purity is transitive too."""
    graph = _internal_graph()
    for module in [m for m in graph if m.startswith("app.engine")]:
        reachable = _reachable(module, graph)
        escaped = sorted(
            m for m in reachable if not m.startswith(("app.engine", "app.domain")) and m != "app"
        )
        assert not escaped, f"{module} can reach {escaped} transitively"


def test_the_transitive_check_would_catch_a_real_violation() -> None:
    """Guard the guard, twice over.

    First on a synthetic graph, then on the real one: a `from app.services import intake`
    added to llm.py must be seen as reaching app.db, because intake imports it. An
    earlier version of this test recorded only the package name and so passed with
    exactly that violation in place.
    """
    synthetic = {
        "app.services.llm": {"app.services.helper"},
        "app.services.helper": {"app.db.repo"},
        "app.db.repo": set(),
    }
    assert "app.db.repo" in _reachable("app.services.llm", synthetic)

    real = _internal_graph()
    assert "app.services.intake" in real, "expected intake to be a known module"
    with_violation = {**real, "app.services.llm": real["app.services.llm"] | {"app.services.intake"}}
    leaked = {
        m for m in _reachable("app.services.llm", with_violation) if m.startswith("app.db")
    }
    assert leaked, "the real graph must expose a database path through app.services.intake"


def test_submodule_imports_are_recorded_not_just_their_package() -> None:
    """`from app.services import intake` must yield app.services.intake as an edge."""
    targets = _import_targets(APP / "api" / "v1" / "determine.py")
    assert "app.services.determination" in targets or "app.services" in targets
    graph = _internal_graph()
    assert "app.services.determination" in graph["app.api.v1.determine"]


# ------------------------------------------------------------------ the payment boundary

BILLING = APP / "services" / "billing.py"


def test_stripe_is_imported_in_exactly_one_module() -> None:
    """Only services/billing.py may import the Stripe SDK, anywhere in the app.

    Same rule as the Anthropic SDK and for the same reason: everything a third party
    controls enters through one file, and that file is the one that gets read carefully.
    """
    importers = [
        path.relative_to(APP)
        for path in _python_files(APP)
        if any(module.split(".")[0] == "stripe" for module, _ in _imports(path))
    ]
    assert importers in ([], [BILLING.relative_to(APP)]), (
        f"stripe may only be imported by services/billing.py; found: {importers}"
    )


def test_billing_has_no_import_path_to_the_engine_or_the_determination_service() -> None:
    """A payment provider must not be able to reach the thing that decides a SAIL.

    Transitive, like the LLM check: billing reads plan definitions and configuration,
    and nothing else.
    """
    graph = _internal_graph()
    reachable = _reachable("app.services.billing", graph)
    forbidden = sorted(
        m
        for m in reachable
        if m.startswith("app.engine") or m == "app.services.determination"
    )
    assert not forbidden, (
        "services/billing.py can reach these transitively:\n  " + "\n  ".join(forbidden)
    )


def test_the_plan_table_depends_on_nothing_at_all() -> None:
    """``plans.py`` is read on every gated request, including where Stripe is absent.

    It must therefore import nothing from ``app`` — a dependency on billing would make
    plan limits unreadable on a deployment with no payment provider configured.
    """
    offenders = [
        f"line {lineno}: {module!r}"
        for module, lineno in _imports(APP / "services" / "plans.py")
        if module.startswith("app")
    ]
    assert not offenders, "services/plans.py must stay free of app imports:\n" + "\n".join(offenders)


def test_the_country_packs_are_not_reachable_from_the_engine() -> None:
    """A national *pack* is administrative. Only the ``.lp`` national files may decide."""
    graph = _internal_graph()
    for module in [m for m in graph if m.startswith("app.engine")]:
        assert "app.national" not in _reachable(module, graph), (
            f"{module} can reach app.national; only the rulebase's 90_national_*.lp files "
            "may change a determination for a country"
        )
