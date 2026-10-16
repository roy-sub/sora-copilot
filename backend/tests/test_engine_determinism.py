"""Determinism, scaling, and the single-answer-set property.

The determination path runs clingo with ``--models=2`` and refuses more than one answer
set: a second model means two rules concluded different values for the same thing, which
is a rulebase bug rather than a runtime ambiguity to resolve by picking one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain import Mission
from app.engine import facts as facts_module
from app.engine.rulebase import generate
from app.engine.runner import mission_hash, solve
from app.engine.scale import density_to_int, ft_to_cm, kg_to_g, m_to_cm, ms_to_cms

GOLDEN = Path(__file__).resolve().parent / "golden"


def _fact_text(name: str) -> str:
    case = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))
    ac = case["aircraft"]
    return facts_module.render(
        Mission.model_validate(case["mission"]),
        drone_max_dimension_m=ac["max_dimension_m"],
        drone_mtom_kg=ac["mtom_kg"],
        drone_max_speed_ms=ac["max_speed_ms"],
        drone_fitted=ac.get("fitted", []),
        adjacent_area_populated=case.get("adjacent_area_populated", False),
    )


@pytest.mark.parametrize(
    "name",
    [
        "powerline-corridor-aerodrome",
        "quarry-controlled-ground",
        "above-150m-controlled",
        "assembly-of-people",
    ],
)
def test_exactly_one_answer_set(name: str) -> None:
    """solve() raises on a second model, so reaching a result proves there was only one."""
    result = solve(_fact_text(name))
    assert result.becauses


def test_the_same_mission_hashes_the_same() -> None:
    case = json.loads((GOLDEN / "powerline-corridor-aerodrome.json").read_text(encoding="utf-8"))
    mission = Mission.model_validate(case["mission"])
    assert mission_hash(mission, "2.5.1") == mission_hash(mission, "2.5.1")


def test_a_different_rulebase_version_hashes_differently() -> None:
    """Idempotency is per (mission, rulebase): a new rulebase means a new determination."""
    case = json.loads((GOLDEN / "powerline-corridor-aerodrome.json").read_text(encoding="utf-8"))
    mission = Mission.model_validate(case["mission"])
    assert mission_hash(mission, "2.5.0-rc1") != mission_hash(mission, "2.5.1")


def test_a_changed_mitigation_hashes_differently() -> None:
    case = json.loads((GOLDEN / "powerline-corridor-aerodrome.json").read_text(encoding="utf-8"))
    mission = Mission.model_validate(case["mission"])
    changed = mission.model_copy(update={"mitigations": []})
    assert mission_hash(mission, "2.5.1") != mission_hash(changed, "2.5.1")


# ------------------------------------------------------------------ scaling


def test_lengths_round_up_so_a_band_is_never_overstated() -> None:
    """A 1.001 m aircraft must not be read as fitting the 1 m column."""
    assert m_to_cm(1.0) == 100
    assert m_to_cm(1.001) == 101
    assert m_to_cm(1.32) == 132


def test_speeds_round_up() -> None:
    assert ms_to_cms(25.0) == 2500
    assert ms_to_cms(25.001) == 2501


def test_mass_is_exact_at_the_small_ua_boundary() -> None:
    """250 g is the provision's boundary; 250.001 g must fall outside it."""
    assert kg_to_g(0.25) == 250
    assert kg_to_g(0.250001) == 251


def test_density_rounds_up_so_a_row_is_never_understated() -> None:
    """Rounding a density down could drop the operation into a lower iGRC row."""
    assert density_to_int(4.0) == 4
    assert density_to_int(4.2) == 5
    assert density_to_int(84) == 84


def test_five_hundred_feet_is_152_point_4_metres() -> None:
    assert ft_to_cm(500) == 15240


# ------------------------------------------------------------------ the generator


def test_the_generated_facts_contain_no_zero_igrc_cell() -> None:
    """An out-of-scope cell must be ABSENT, not emitted as 0."""
    text = generate.render()
    assert "igrc_cell(over_50000, 3," not in text
    assert "igrc_cell(over_50000, 1, 7)." in text


def test_the_generator_marks_every_unverified_table() -> None:
    text = generate.render()
    # Nothing is unverified any more, so nothing is marked. A stale marker here would
    # put an UNVERIFIED banner on a determination that has outgrown it.
    assert "table_unverified(" not in text


def test_boolean_cells_are_emitted_as_constants_not_strings() -> None:
    """A string here and a constant in 00_core.lp would ground cleanly and match nothing."""
    text = generate.render()
    # arc_rule(priority, aec, atypical, ...) — the AEC sits between the two.
    assert "arc_rule(1, 12, true," in text
    assert 'arc_rule(1, 12, "true",' not in text


def test_regenerating_is_byte_identical() -> None:
    """The rulebase must be reproducible: same CSVs in, same program out."""
    assert generate.render() == generate.render()
