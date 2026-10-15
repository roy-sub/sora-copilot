"""What minimal change reaches a lower SAIL.

**Bounded combination search over the real engine.** Candidate changes are enumerated,
then combinations of increasing size are tried — size 1 first, then size 2 — and each
combination is scored by RE-RUNNING clingo. The search stops at the smallest size that
finds anything, so what comes back is minimal.

Single-parameter search alone is not enough, and that is not a theoretical concern: for a
sparsely-populated BVLOS corridor inside an aerodrome environment with nothing claimed,
no single change lowers SAIL at all, because the operation needs a ground-risk reduction
AND an air-risk reduction together. An advisor that answers "nothing helps" there is worse
than no advisor, so pairs are searched.

**Why not Z3.** The build spec offers Z3 optimisation over the encoded tables as the
phase-7 upgrade. That would mean encoding the SORA tables a second time, in SMT, beside
the clingo encoding — two implementations of the same compliance rules, which is exactly
the failure this architecture exists to prevent. The spec's own safeguard for that risk
is "a cross-check test that both agree", which is an admission that they might not.
Searching combinations against the one authoritative engine is slower and completely
sound: every suggestion offered is a SAIL the solver actually produced. At ~16 ms per run
a pair search costs about a second, which is affordable for an interactive advisor.

Ranking uses an effort cost from ``tables/cf_costs.csv``, which is **ours, not the
regulation's**: it orders the list and never touches a determination.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import cast

from app.domain import CounterfactualChange, CounterfactualSuggestion, Mission, MitigationClaim
from app.domain.common import GroundEnvironment, MitigationKind, OperationType, Robustness
from app.domain.determination import Determination
from app.engine.rulebase.loader import load_rulebase
from app.engine.runner import UnsatisfiableMission, determine
from app.engine.scale import ft_to_cm

SAIL_INDEX = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "certified_category": 7}

#: Just below 500 ft, so lowering the altitude actually crosses the band boundary.
BELOW_BAND_ALTITUDE_M = round((ft_to_cm(500) - 100) / 100, 1)


@dataclass(frozen=True, slots=True)
class Aircraft:
    """The aircraft figures the engine needs, passed in rather than looked up."""

    max_dimension_m: float
    mtom_kg: float
    max_speed_ms: float
    fitted: tuple[str, ...] = ()


@lru_cache
def _costs(version_dir: str = "sora_2_5") -> dict[str, tuple[float, str, str]]:
    return {
        r["parameter"]: (float(r["effort_cost"]), r["label"], r["evidence_required"])
        for r in load_rulebase(version_dir)["cf_costs"].rows
    }


def _with_mitigation(mission: Mission, kind: str, robustness: Robustness) -> Mission:
    claims = [m for m in mission.mitigations if m.kind != kind]
    if robustness is not Robustness.NONE:
        claims.append(MitigationClaim(kind=cast("MitigationKind", kind), robustness=robustness))
    return mission.model_copy(update={"mitigations": claims})


def _candidates(mission: Mission, aircraft: Aircraft) -> list[tuple[str, Mission]]:
    """Every single change worth trying, as (cost key, changed mission)."""
    out: list[tuple[str, Mission]] = []
    current: dict[str, Robustness] = {str(m.kind): m.robustness for m in mission.mitigations}

    def claimed(kind: str) -> Robustness:
        return current.get(kind, Robustness.NONE)

    # M1 sheltering: low then medium, skipping whatever is already claimed.
    for level in (Robustness.LOW, Robustness.MEDIUM):
        if claimed("m1_strategic") is not level:
            out.append(
                (f"mitigations.m1_strategic.{level.value}", _with_mitigation(mission, "m1_strategic", level))
            )

    # M1 ground observation: low only.
    if claimed("m1_ers") is not Robustness.LOW:
        out.append(("mitigations.m1_ers.low", _with_mitigation(mission, "m1_ers", Robustness.LOW)))

    # M2 impact reduction needs a parachute fitted, so only offer it when there is one.
    if any("parachute" in f.lower() for f in aircraft.fitted):
        for level in (Robustness.MEDIUM, Robustness.HIGH):
            if claimed("m2_impact") is not level:
                out.append(
                    (f"mitigations.m2_impact.{level.value}", _with_mitigation(mission, "m2_impact", level))
                )

    # Strategic air risk mitigation.
    if claimed("strategic_air") is Robustness.NONE:
        out.append(
            ("mitigations.strategic_air.claimed", _with_mitigation(mission, "strategic_air", Robustness.LOW))
        )

    # Lower the altitude below the 500 ft band boundary.
    if mission.volume.max_altitude_agl_m > BELOW_BAND_ALTITUDE_M:
        volume = mission.volume.model_copy(update={"max_altitude_agl_m": BELOW_BAND_ALTITUDE_M})
        out.append(("volume.max_altitude_agl_m", mission.model_copy(update={"volume": volume})))

    # Leave the aerodrome environment.
    if mission.near_aerodrome:
        out.append(("near_aerodrome.false", mission.model_copy(update={"near_aerodrome": False})))

    # Move to a less populated ground environment, one band at a time.
    ladder = [
        GroundEnvironment.ASSEMBLY,
        GroundEnvironment.POPULATED,
        GroundEnvironment.SPARSELY_POPULATED,
        GroundEnvironment.CONTROLLED,
    ]
    if mission.ground_environment in ladder:
        index = ladder.index(mission.ground_environment)
        if index + 1 < len(ladder):
            nicer = ladder[index + 1]
            update: dict[str, object] = {"ground_environment": nicer}
            # A controlled ground area has no density row, and a quieter band needs a
            # density that actually sits in it, or the change would not be real.
            if nicer is GroundEnvironment.CONTROLLED:
                update["population_density_per_km2"] = None
            elif mission.population_density_per_km2 is not None:
                update["population_density_per_km2"] = min(mission.population_density_per_km2, 4)
            out.append(("ground_environment.sparsely_populated", mission.model_copy(update=update)))

    # Reduce to VLOS. Expensive, because it usually removes the reason for the flight.
    if mission.operation_type is not OperationType.VLOS:
        out.append(("operation_type.vlos", mission.model_copy(update={"operation_type": OperationType.VLOS})))

    return out


def _effect(before: Determination, after: Determination) -> str:
    parts: list[str] = []
    if before.igrc != after.igrc:
        parts.append(f"iGRC {before.igrc} → {after.igrc}")
    if before.final_grc != after.final_grc:
        parts.append(f"GRC {before.final_grc} → {after.final_grc}")
    if before.initial_arc != after.initial_arc:
        parts.append(f"ARC {before.initial_arc.value} → {after.initial_arc.value}")
    if before.residual_arc != after.residual_arc:
        parts.append(f"residual ARC {before.residual_arc.value} → {after.residual_arc.value}")
    return " · ".join(parts) or "no change to the chain"


def _oso_delta(before: Determination, after: Determination) -> list[str]:
    was = {o.oso_id: o.required_robustness for o in before.osos}
    now = {o.oso_id: o.required_robustness for o in after.osos}
    out: list[str] = []
    for oso_id in sorted(set(was) | set(now)):
        a, b = was.get(oso_id), now.get(oso_id)
        if a == b:
            continue
        if b is None:
            out.append(f"{oso_id} no longer applies")
        elif a is None:
            out.append(f"{oso_id} now required at {b.value}")
        else:
            out.append(f"{oso_id} {a.value} → {b.value}")
    return out


def _family(key: str) -> str:
    """Changes in the same family are mutually exclusive — you claim M1 at one level."""
    parts = key.split(".")
    if key.startswith("mitigations."):
        return f"mitigations.{parts[1]}"
    return parts[0]


def _apply_all(mission: Mission, keys: tuple[str, ...], aircraft: Aircraft) -> Mission | None:
    """Compose several single changes onto one mission.

    Recomposed from scratch rather than chained, so the order changes are applied in
    cannot affect the result.
    """
    out = mission
    for key in keys:
        changed = _single(out, key, aircraft)
        if changed is None:
            return None
        out = changed
    return out


def _single(mission: Mission, key: str, aircraft: Aircraft) -> Mission | None:
    """Apply one candidate change to a mission, or None if it does not apply to it."""
    for candidate_key, changed in _candidates(mission, aircraft):
        if candidate_key == key:
            return changed
    return None


def _title_for(changes: list[CounterfactualChange]) -> str:
    if len(changes) == 1:
        return changes[0].label
    first = changes[0].label
    others = [c.label[0].lower() + c.label[1:] for c in changes[1:]]
    return first + ", and " + ", and ".join(others)


def suggest(
    mission: Mission,
    aircraft: Aircraft,
    *,
    target_sail: str | None = None,
    adjacent_area_populated: bool = False,
    version_dir: str = "sora_2_5",
    limit: int = 6,
    max_changes: int = 2,
) -> list[CounterfactualSuggestion]:
    """Minimal change sets that lower SAIL, best first. Each one is re-run, not predicted."""

    def run(m: Mission) -> Determination:
        return determine(
            m,
            drone_max_dimension_m=aircraft.max_dimension_m,
            drone_mtom_kg=aircraft.mtom_kg,
            drone_max_speed_ms=aircraft.max_speed_ms,
            drone_fitted=list(aircraft.fitted),
            adjacent_area_populated=adjacent_area_populated,
            version_dir=version_dir,
        )

    base = run(mission)
    base_index = SAIL_INDEX[str(base.sail)]
    if base_index <= 1 and target_sail is None:
        return []  # already at SAIL I; there is nothing below it
    ceiling = SAIL_INDEX[target_sail] if target_sail else base_index - 1

    costs = _costs(version_dir)
    candidates = _candidates(mission, aircraft)
    if not candidates:
        return []

    # Score every single change once. Those results are reused by the pair search, so a
    # pair costs one extra solve rather than three.
    singles: dict[str, Determination] = {}
    for key, changed in candidates:
        try:
            singles[key] = run(changed)
        except UnsatisfiableMission:
            # A change the rulebase refuses is not a suggestion: the operator cannot act
            # on it, and offering it would imply they could.
            continue

    found: list[CounterfactualSuggestion] = []

    def record(keys: tuple[str, ...], after: Determination) -> None:
        changes = [_change(mission, key, aircraft, costs) for key in keys]
        found.append(
            CounterfactualSuggestion(
                id="+".join(keys),
                title=_title_for(changes),
                changes=changes,
                resulting_sail=after.sail,
                chain_effect=_effect(base, after),
                oso_delta=_oso_delta(base, after),
                evidence_required=" ".join(dict.fromkeys(c.evidence_required for c in changes)),
                effort_cost=round(sum(c.effort_cost for c in changes), 3),
            )
        )

    for key, after in singles.items():
        index = SAIL_INDEX[str(after.sail)]
        if index < base_index and index <= ceiling:
            record((key,), after)

    # Only go wider when nothing smaller worked. "Minimal" means minimal.
    if not found and max_changes >= 2:
        # Pair only changes that moved something: two changes that each moved nothing
        # cannot combine into one that does.
        movers = [k for k, d in singles.items() if _effect(base, d) != "no change to the chain"]
        seen: set[frozenset[str]] = set()
        for i, first in enumerate(movers):
            for second in movers[i + 1 :]:
                if _family(first) == _family(second):
                    continue  # mutually exclusive levels of the same mitigation
                pair = frozenset((first, second))
                if pair in seen:
                    continue
                seen.add(pair)
                combined = _apply_all(mission, (first, second), aircraft)
                if combined is None:
                    continue
                try:
                    after = run(combined)
                except UnsatisfiableMission:
                    continue
                index = SAIL_INDEX[str(after.sail)]
                if index < base_index and index <= ceiling:
                    record((first, second), after)

    found.sort(key=lambda s: (SAIL_INDEX[str(s.resulting_sail)], len(s.changes), s.effort_cost))
    return found[:limit]


def _change(
    mission: Mission, key: str, aircraft: Aircraft, costs: dict[str, tuple[float, str, str]]
) -> CounterfactualChange:
    cost, label, evidence = costs.get(key, (99.0, key, "Unknown — this change is not in cf_costs.csv"))
    changed = _single(mission, key, aircraft)
    return CounterfactualChange(
        field=_family(key),
        from_value=_value(mission, key),
        to_value=_value(changed, key) if changed is not None else None,
        label=_title(label, key, aircraft),
        evidence_required=evidence,
        effort_cost=cost,
    )


def _title(label: str, key: str, aircraft: Aircraft) -> str:
    """Name the operator's own equipment where we can, rather than speaking in general."""
    if key.startswith("mitigations.m2_impact") and any("parachute" in f.lower() for f in aircraft.fitted):
        level = key.rsplit(".", 1)[1]
        return f"Claim the parachute already fitted as M2 at {level} robustness"
    if key == "volume.max_altitude_agl_m":
        return f"Lower the maximum altitude to {BELOW_BAND_ALTITUDE_M:g} m AGL, below the 500 ft band"
    return label


def _value(mission: Mission | None, key: str) -> object:
    """The value of the parameter a candidate key names, before or after the change."""
    if mission is None:
        return None
    if key.startswith("mitigations."):
        kind = cast("MitigationKind", key.split(".")[1])
        claim = mission.mitigation(kind)
        return claim.robustness.value if claim else "none"
    if key == "volume.max_altitude_agl_m":
        return mission.volume.max_altitude_agl_m
    if key == "near_aerodrome.false":
        return mission.near_aerodrome
    if key.startswith("ground_environment"):
        return mission.ground_environment.value
    if key.startswith("operation_type"):
        return mission.operation_type.value
    return None
