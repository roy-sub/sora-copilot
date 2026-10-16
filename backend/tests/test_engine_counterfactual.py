"""Counterfactuals.

Every suggestion is verified by re-running the real engine, so the SAIL a suggestion
claims is one the solver actually produced. Nothing here predicts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain import Mission
from app.engine.counterfactual import SAIL_INDEX, Aircraft, suggest
from app.engine.runner import determine

GOLDEN = Path(__file__).resolve().parent / "golden"


def _case(name: str) -> tuple[Mission, Aircraft, bool]:
    raw = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))
    ac = raw["aircraft"]
    return (
        Mission.model_validate(raw["mission"]),
        Aircraft(
            max_dimension_m=ac["max_dimension_m"],
            mtom_kg=ac["mtom_kg"],
            max_speed_ms=ac["max_speed_ms"],
            fitted=tuple(ac.get("fitted", [])),
        ),
        raw.get("adjacent_area_populated", False),
    )


def _determine(mission: Mission, aircraft: Aircraft, adjacent: bool):
    return determine(
        mission,
        drone_max_dimension_m=aircraft.max_dimension_m,
        drone_mtom_kg=aircraft.mtom_kg,
        drone_max_speed_ms=aircraft.max_speed_ms,
        drone_fitted=list(aircraft.fitted),
        adjacent_area_populated=adjacent,
    )


@pytest.mark.parametrize(
    "name", ["powerline-corridor-no-mitigations", "roof-survey-populated", "above-150m-controlled"]
)
def test_every_suggestion_actually_lowers_sail(name: str) -> None:
    """The whole point. A suggestion that does not lower SAIL is noise in a safety tool."""
    mission, aircraft, adjacent = _case(name)
    base = _determine(mission, aircraft, adjacent)
    base_index = SAIL_INDEX[str(base.sail)]

    out = suggest(mission, aircraft, adjacent_area_populated=adjacent)
    assert out, f"{name}: the advisor found nothing; check whether a change set exists"
    for s in out:
        assert SAIL_INDEX[str(s.resulting_sail)] < base_index, s.title


@pytest.mark.parametrize(
    "name", ["powerline-corridor-no-mitigations", "roof-survey-populated", "above-150m-controlled"]
)
def test_suggestions_are_ranked_best_first(name: str) -> None:
    mission, aircraft, adjacent = _case(name)
    out = suggest(mission, aircraft, adjacent_area_populated=adjacent)
    ranks = [(SAIL_INDEX[str(s.resulting_sail)], s.change_count, s.effort_cost) for s in out]
    assert ranks == sorted(ranks)


def test_each_suggestion_says_what_evidence_it_needs() -> None:
    mission, aircraft, adjacent = _case("powerline-corridor-no-mitigations")
    out = suggest(mission, aircraft, adjacent_area_populated=adjacent)
    assert out
    for s in out:
        assert s.evidence_required
        assert s.chain_effect
        assert s.changes
        for change in s.changes:
            assert change.label
            assert change.evidence_required


def test_a_suggestion_applied_reproduces_the_sail_it_promised() -> None:
    """Re-run each suggested change set independently and confirm the promise holds.

    This is the property the advisor lives or dies on: a suggestion that does not
    actually produce the SAIL it claims would send an operator to their authority with a
    number the engine never computed.
    """
    from app.engine.counterfactual import _apply_all

    mission, aircraft, adjacent = _case("powerline-corridor-no-mitigations")
    offered = suggest(mission, aircraft, adjacent_area_populated=adjacent)
    assert offered
    for s in offered:
        combined = _apply_all(mission, tuple(s.id.split("+")), aircraft)
        assert combined is not None, s.id
        again = _determine(combined, aircraft, adjacent)
        assert str(again.sail) == str(s.resulting_sail), s.title


def test_pairs_are_searched_only_when_no_single_change_works() -> None:
    """ "Minimal" has to mean minimal: never offer two changes where one would do."""
    mission, aircraft, adjacent = _case("above-150m-controlled")
    out = suggest(mission, aircraft, adjacent_area_populated=adjacent)
    assert out
    assert all(s.change_count == 1 for s in out)


def test_a_pair_is_found_where_no_single_change_can_work() -> None:
    """The case that motivated combination search.

    A sparsely-populated BVLOS corridor inside an aerodrome environment with nothing
    claimed needs a ground-risk reduction AND an air-risk reduction together. Single-
    parameter search reports nothing here, which would be a false negative in a safety
    tool.
    """
    mission, aircraft, adjacent = _case("powerline-corridor-no-mitigations")
    singles_only = suggest(mission, aircraft, adjacent_area_populated=adjacent, max_changes=1)
    assert singles_only == []

    pairs = suggest(mission, aircraft, adjacent_area_populated=adjacent, max_changes=2)
    assert pairs, "pair search found nothing where a pair demonstrably exists"
    assert all(s.change_count == 2 for s in pairs)


def test_a_suggestion_never_claims_one_mitigation_at_two_levels() -> None:
    mission, aircraft, adjacent = _case("powerline-corridor-no-mitigations")
    for s in suggest(mission, aircraft, adjacent_area_populated=adjacent):
        families = [c.field for c in s.changes]
        assert len(families) == len(set(families)), s.title


def test_suggestions_are_bounded_in_number() -> None:
    mission, aircraft, adjacent = _case("powerline-corridor-no-mitigations")
    assert len(suggest(mission, aircraft, adjacent_area_populated=adjacent, limit=3)) <= 3


def test_m2_is_not_offered_without_a_parachute() -> None:
    """Suggesting equipment the aircraft does not have wastes the operator's time."""
    mission, _, adjacent = _case("powerline-corridor-no-mitigations")
    bare = Aircraft(max_dimension_m=1.32, mtom_kg=15.9, max_speed_ms=22, fitted=())
    out = suggest(mission, bare, adjacent_area_populated=adjacent)
    assert not any(s.id.startswith("mitigations.m2_impact") for s in out)


def test_m2_is_offered_when_a_parachute_is_fitted() -> None:
    from app.engine.counterfactual import _candidates

    mission, _, _unused = _case("powerline-corridor-no-mitigations")
    with_chute = Aircraft(max_dimension_m=1.32, mtom_kg=15.9, max_speed_ms=22, fitted=("parachute",))
    considered = {k for k, _ in _candidates(mission, with_chute)}
    assert any(k.startswith("mitigations.m2_impact") for k in considered)


def test_no_suggestions_when_already_at_the_lowest_sail() -> None:
    mission, aircraft, adjacent = _case("quarry-controlled-ground")
    base = _determine(mission, aircraft, adjacent)
    out = suggest(mission, aircraft, adjacent_area_populated=adjacent)
    for s in out:
        assert SAIL_INDEX[str(s.resulting_sail)] < SAIL_INDEX[str(base.sail)]


def test_a_target_sail_filters_to_suggestions_that_reach_it() -> None:
    """A target is a filter on the answer, not a cap on the number of answers.

    This asserted len(narrow) <= len(everything), which held by accident. The search
    only looks at pairs of changes when no single change reaches the goal, so a harder
    target can legitimately return MORE suggestions than an easier one: three single
    changes that each drop one SAIL, against four combinations that drop two.
    """
    mission, aircraft, adjacent = _case("above-150m-controlled")
    everything = suggest(mission, aircraft, adjacent_area_populated=adjacent)
    narrow = suggest(mission, aircraft, target_sail="II", adjacent_area_populated=adjacent)

    assert narrow, "the target is reachable, so something should reach it"
    for s in narrow:
        assert SAIL_INDEX[str(s.resulting_sail)] <= SAIL_INDEX["II"]
    # And the target changes the answer rather than being ignored: without it the
    # advisor is happy to offer a change that stops one SAIL short.
    assert any(SAIL_INDEX[str(s.resulting_sail)] > SAIL_INDEX["II"] for s in everything)
