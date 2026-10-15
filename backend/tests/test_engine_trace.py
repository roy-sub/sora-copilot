"""The trace contract.

The product's promise is "every line cites its rule". These tests are what makes that a
property of the code rather than a slogan: a conclusion without a justification cannot
exist, and a rule without a citation is refused.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.domain import Mission
from app.engine.rulebase.loader import load_rulebase
from app.engine.runner import determine, solve
from app.engine.trace import TraceError, build, citation_for

GOLDEN = Path(__file__).resolve().parent / "golden"
CASE = GOLDEN / "powerline-corridor-aerodrome.json"


@pytest.fixture
def determination():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    ac = case["aircraft"]
    return determine(
        Mission.model_validate(case["mission"]),
        drone_max_dimension_m=ac["max_dimension_m"],
        drone_mtom_kg=ac["mtom_kg"],
        drone_max_speed_ms=ac["max_speed_ms"],
        drone_fitted=ac["fitted"],
        adjacent_area_populated=case["adjacent_area_populated"],
    )


def test_every_trace_node_has_a_citation(determination) -> None:
    for node in determination.trace:
        assert node.citation.document, f"{node.id} has no document"
        assert node.citation.section, f"{node.id} has no section"


def test_every_trace_node_has_a_rule_id(determination) -> None:
    for node in determination.trace:
        assert node.rule_id, f"{node.id} has no rule id"


def test_every_premise_points_at_a_real_node(determination) -> None:
    ids = {n.id for n in determination.trace}
    for node in determination.trace:
        for premise in node.premises:
            assert premise in ids, f"{node.id} cites premise {premise!r}, which is not a node"


def test_the_trace_has_a_root_reachable_from_the_leaves(determination) -> None:
    by_id = {n.id for n in determination.trace}
    roots = [n for n in determination.trace if n.conclusion.startswith("SAIL =")]
    assert len(roots) == 1
    # Walking down from the root must reach at least one operator-input leaf.
    nodes = {n.id: n for n in determination.trace}
    seen: set[str] = set()
    stack = [roots[0].id]
    facts: list[str] = []
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        node = nodes[current]
        if node.kind == "fact":
            facts.append(current)
        stack.extend(p for p in node.premises if p in by_id)
    assert facts, "the root is not connected to any confirmed fact"


def test_derived_nodes_rest_on_something(determination) -> None:
    for node in determination.trace:
        if node.kind in ("rule", "override"):
            assert node.premises, f"{node.id} is derived but rests on nothing"


def test_operator_facts_are_distinguished_from_table_rows(determination) -> None:
    """A table row is a premise, but it must cite the table, not the operator."""
    facts = [n for n in determination.trace if n.kind == "fact"]
    assert facts
    for node in facts:
        assert node.citation.document == "Operator input"
    tables = [n for n in determination.trace if n.rule_id.startswith("table.")]
    assert tables, "expected at least one table-row premise"
    for node in tables:
        assert node.citation.document != "Operator input"


def test_unverified_tables_are_reported_to_the_user(determination) -> None:
    assert determination.warnings
    assert any("UNVERIFIED" in w for w in determination.warnings)
    assert determination.is_verified is False


def test_a_rule_id_with_no_citation_is_refused() -> None:
    with pytest.raises(TraceError, match=re.escape("citations.csv")):
        citation_for("sora25.invented.rule")


def test_building_a_trace_with_no_because_atoms_is_refused() -> None:
    with pytest.raises(TraceError, match=r"because/3"):
        build([])


def test_every_rule_id_the_rulebase_can_fire_has_a_citation() -> None:
    """Scan the .lp sources for rule-id literals and check each one is in the index."""
    import re

    from app.engine.rulebase.loader import RULEBASE_ROOT
    from app.engine.runner import PROGRAM_ORDER

    cited = {r["rule_id"] for r in load_rulebase()["citations"].rows}
    pattern = re.compile(r'because\([^,]+,\s*"([^"]+)"')
    missing: set[str] = set()
    for name in PROGRAM_ORDER:
        text = (RULEBASE_ROOT / "sora_2_5" / name).read_text(encoding="utf-8")
        # Skip comments: 00_core.lp documents the because/3 pattern with a placeholder
        # rule id, which is prose rather than a rule the engine can fire.
        code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("%"))
        for rule_id in pattern.findall(code):
            if rule_id not in cited:
                missing.add(f"{name}: {rule_id}")
    assert not missing, "rule ids with no citation: " + ", ".join(sorted(missing))


def test_the_justification_constraint_is_live() -> None:
    """Prove the integrity constraint actually fires, rather than trusting that it would.

    An unjustified conclusion is injected; the program must become unsatisfiable.
    """
    from app.engine.runner import UnsatisfiableMission

    case = json.loads(CASE.read_text(encoding="utf-8"))
    ac = case["aircraft"]
    from app.engine import facts as facts_module

    fact_text = facts_module.render(
        Mission.model_validate(case["mission"]),
        drone_max_dimension_m=ac["max_dimension_m"],
        drone_mtom_kg=ac["mtom_kg"],
        drone_max_speed_ms=ac["max_speed_ms"],
        drone_fitted=ac["fitted"],
    )
    # A conclusion nobody justified.
    injected = fact_text + "\nconclusion_atom(smuggled_conclusion).\n"
    with pytest.raises(UnsatisfiableMission) as exc:
        solve(injected)
    assert any("without a justification" in r for r in exc.value.reasons), exc.value.reasons
