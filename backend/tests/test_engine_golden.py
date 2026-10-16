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
def test_golden_case_records_that_it_pins_the_adopted_text(path: Path) -> None:
    """Every case states which it pins: the seed, or the regulation.

    It used to assert the first. The tables are transcribed from the adopted AMC now, so
    a case that still claimed to pin a seed would be claiming less than it does — and
    the flag is what tells a reader whether a stored determination can be defended.
    """
    case = json.loads(path.read_text(encoding="utf-8"))
    assert case["verified_against_official_text"] is True
    assert case["note"].strip(), "a case has to say what it is pinning and why"


@pytest.mark.parametrize("path", _cases(unsat=False), ids=lambda p: p.stem)
def test_golden_case_is_deterministic(path: Path) -> None:
    """The same mission and rulebase must give the same determination, every time."""
    case = json.loads(path.read_text(encoding="utf-8"))
    first, second = _run(case), _run(case)
    assert first.mission_hash == second.mission_hash
    assert [n.model_dump() for n in first.trace] == [n.model_dump() for n in second.trace]
    assert first.sail == second.sail


# ---------------------------------------------------------------- Step #8, by hand

#: Table 11 of AMC1 Article 11 (8 m UA), SAIL IV row. Each case is a pair of Step #8
#: inputs and the column it should land in, walked by hand from the printed table.
#: The golden cases pin whole determinations; this pins the column rule itself, which
#: is the part with a reading of the regulation in it — S.4.8.3(d)'s "most stringent
#: between the value of the average population density and the outdoor assembly of
#: people" decides between two columns, and getting it backwards still produces a
#: plausible level.
TABLE_11_SAIL_IV = [
    (90_000.0, "over_400k", None, "column 1: no upper limit on either, and SAIL IV is out of scope there"),
    (40_000.0, "40k_to_400k", "medium", "column 2: under 50 000 and assemblies under 400k"),
    (4_000.0, "under_40k", "low", "column 3: under 5 000"),
    (420.0, "under_40k", "low", "column 4: under 500"),
    (10.0, "under_40k", "low", "column 5: under 50"),
    (10.0, "40k_to_400k", "medium",
     "density supports column 5, the assembly only column 2 — the assembly governs"),
]


@pytest.mark.parametrize(
    ("density", "assembly", "level", "why"),
    TABLE_11_SAIL_IV,
    ids=[c[3].split(":")[0] for c in TABLE_11_SAIL_IV],
)
def test_step_8_picks_the_column_the_table_prints(
    density: float, assembly: str, level: str | None, why: str
) -> None:
    case = json.loads(
        (GOLDEN / "containment-computed-from-table-11.json").read_text(encoding="utf-8")
    )
    case["mission"]["adjacent_area_density_per_km2"] = density
    case["mission"]["adjacent_assembly_size"] = assembly
    d = _run(case)
    assert d.sail.value == "IV", "the fixture has to stay on the SAIL row this table walks"
    assert d.containment.level == level, why
    # "Out of scope" is not a level, and must not be reported as one.
    assert d.containment.assessment_required is (level is None)


def test_step_8_says_which_kind_of_no_answer_it_is() -> None:
    """Out of scope and "you have not told me" are different answers, not one.

    Both come back with no level and assessment_required true. Merging them would put a
    regulatory conclusion and a gap in a form behind the same sentence.
    """
    case = json.loads(
        (GOLDEN / "containment-computed-from-table-11.json").read_text(encoding="utf-8")
    )
    missing = json.loads(json.dumps(case))
    missing["mission"]["adjacent_area_density_per_km2"] = None
    missing["mission"]["adjacent_assembly_size"] = None
    assert "Supply both" in _run(missing).containment.note

    scope = json.loads(json.dumps(case))
    scope["mission"]["adjacent_area_density_per_km2"] = 90_000.0
    scope["mission"]["adjacent_assembly_size"] = "over_400k"
    assert "Out of scope" in _run(scope).containment.note
