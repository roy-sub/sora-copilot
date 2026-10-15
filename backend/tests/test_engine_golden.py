"""Golden cases: worked missions with expected chains.

Each case in ``tests/golden/`` is a mission, an aircraft, and the chain the engine must
produce. **An engine change may not land with a failing golden case.**

What these cases are NOT: regulatory truth. Every table in the rulebase is still a seed
(``verified: false``), so a case pins the *seed's* behaviour. When a table is verified
against the official document, the affected cases must be re-derived FROM THAT DOCUMENT
before the engine is touched — a case that merely encodes the seed's mistake would
otherwise lock the mistake in. Each file records that in its ``note``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain import Mission
from app.engine.runner import UnsatisfiableMission, determine

GOLDEN = Path(__file__).resolve().parent / "golden"


def _cases(unsat: bool) -> list[Path]:
    return sorted(p for p in GOLDEN.glob("*.json") if p.name.startswith("unsat-") is unsat)


def _run(case: dict[str, object]):
    mission = Mission.model_validate(case["mission"])
    ac = case["aircraft"]
    assert isinstance(ac, dict)
    return determine(
        mission,
        drone_max_dimension_m=float(ac["max_dimension_m"]),
        drone_mtom_kg=float(ac["mtom_kg"]),
        drone_max_speed_ms=float(ac["max_speed_ms"]),
        drone_fitted=list(ac.get("fitted", [])),
        adjacent_area_populated=bool(case.get("adjacent_area_populated", False)),
    )


def test_there_are_golden_cases() -> None:
    """A vacuous pass would be worse than a failure."""
    assert len(_cases(unsat=False)) >= 8
    assert len(_cases(unsat=True)) >= 3


@pytest.mark.parametrize("path", _cases(unsat=False), ids=lambda p: p.stem)
def test_golden_case_reproduces_its_chain(path: Path) -> None:
    case = json.loads(path.read_text(encoding="utf-8"))
    expect = case["expect"]
    d = _run(case)

    sail = d.sail if isinstance(d.sail, str) else d.sail.value
    actual = {
        "igrc": d.igrc,
        "final_grc": d.final_grc,
        "initial_arc": d.initial_arc.value,
        "residual_arc": d.residual_arc.value,
        "sail": sail,
        "tmpr": d.tmpr,
        "osos_required": sum(1 for o in d.osos if o.is_required),
        "osos_total": len(d.osos),
        "containment_assessment_required": d.containment.assessment_required,
        "containment_level": d.containment.level,
        "trace_node_count": len(d.trace),
        "root_rule_id": expect["root_rule_id"],
    }
    assert actual == expect, f"{case['name']}: {case['description']}"


@pytest.mark.parametrize("path", _cases(unsat=True), ids=lambda p: p.stem)
def test_golden_case_is_refused(path: Path) -> None:
    """Inputs the rulebase must refuse.

    Accepting any of these would mean a determination computed from a mitigation the
    table does not offer — a number with no rule behind it.
    """
    case = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(UnsatisfiableMission) as exc:
        _run(case)
    assert exc.value.reasons, "a refusal must say why"
    for expected in case.get("expect_reasons", []):
        assert expected in exc.value.reasons


@pytest.mark.parametrize("path", _cases(unsat=False), ids=lambda p: p.stem)
def test_golden_case_records_that_it_is_unverified(path: Path) -> None:
    """Every case must state it pins the seed rather than the regulation."""
    case = json.loads(path.read_text(encoding="utf-8"))
    assert case["verified_against_official_text"] is False
    assert "verified" in case["note"]


@pytest.mark.parametrize("path", _cases(unsat=False), ids=lambda p: p.stem)
def test_golden_case_is_deterministic(path: Path) -> None:
    """The same mission and rulebase must give the same determination, every time."""
    case = json.loads(path.read_text(encoding="utf-8"))
    first, second = _run(case), _run(case)
    assert first.mission_hash == second.mission_hash
    assert [n.model_dump() for n in first.trace] == [n.model_dump() for n in second.trace]
    assert first.sail == second.sail
