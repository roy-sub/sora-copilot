"""Orchestration: a confirmed mission becomes a stored determination.

The sequence, and nothing else: load the operation and its facts → fold in the
**confirmed** facts → assemble a validated ``Mission`` → load the aircraft → render ASP
facts → run clingo → build the trace → persist with the rulebase version pinned.

Idempotent per (operation, mission hash, rulebase version): re-running with identical
input returns the determination already stored rather than computing a second one with a
new id, because a dossier references a determination by id and two ids for one
computation would make the record ambiguous.

This module imports the engine. ``services/llm.py`` must never import this module — the
boundary test asserts it.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.repo import NotFound, Repo, Row
from app.domain import Determination, Mission
from app.engine.counterfactual import Aircraft, suggest
from app.engine.rulebase.loader import rulebase_version as rulebase_version_of
from app.engine.runner import UnsatisfiableMission, determine, mission_hash
from app.services import geo, intake


class DeterminationError(RuntimeError):
    """The determination could not be produced. Nothing partial is ever stored."""


def _aircraft(repo: Repo, org_id: UUID, drone_id: UUID) -> Aircraft:
    try:
        drone = repo.get_drone(org_id, drone_id)
    except NotFound as exc:
        raise DeterminationError(
            "the aircraft this operation names is not in your fleet any more. "
            "Pick an aircraft in the wizard and run the determination again."
        ) from exc
    return Aircraft(
        max_dimension_m=float(drone["max_dimension_m"]),
        mtom_kg=float(drone["mtom_kg"]),
        max_speed_ms=float(drone["max_speed_ms"]),
        fitted=tuple(drone.get("fitted_mitigations") or ()),
    )


def confirmed_mission(repo: Repo, org_id: UUID, operation_id: UUID) -> Mission:
    """The mission the engine is allowed to see, or a readable refusal.

    Raises ``UnconfirmedFacts`` while anything the model proposed is still pending. That
    is the gate: there is no argument to this function that bypasses it.
    """
    operation = repo.get_operation(org_id, operation_id)
    facts = repo.list_facts(operation_id)

    pending = intake.unconfirmed_fields(facts)
    if pending:
        raise intake.UnconfirmedFacts(pending)

    draft = intake.apply_confirmed(dict(operation.get("mission") or {}), facts)
    return intake.build_mission(operation=operation, confirmed_draft=draft, org_id=org_id)


def adjacent_area_is_populated(repo: Repo, operation_id: UUID) -> bool:
    """Whether the sampled adjacent area is populated, for the containment step.

    Absent geo facts mean "not established", which is reported as false and shown in the
    containment note — it is never inferred from the flight geography.
    """
    row = repo.get_geo_facts(operation_id)
    if not row:
        return False
    return bool(row.get("adjacent_area_populated", False))


def run(
    repo: Repo,
    org_id: UUID,
    operation_id: UUID,
    *,
    force: bool = False,
) -> tuple[Determination, bool]:
    """Compute and persist. Returns the determination and whether it was freshly computed."""
    mission = confirmed_mission(repo, org_id, operation_id)
    aircraft = _aircraft(repo, org_id, mission.drone_id)
    rulebase = _pinned_rulebase(repo, org_id)
    adjacent = adjacent_area_is_populated(repo, operation_id)

    digest = mission_hash(mission, rulebase)
    if not force:
        existing = repo.find_determination(operation_id, digest, rulebase)
        if existing:
            return Determination.model_validate(_from_row(existing)), False

    try:
        determination = determine(
            mission,
            drone_max_dimension_m=aircraft.max_dimension_m,
            drone_mtom_kg=aircraft.mtom_kg,
            drone_max_speed_ms=aircraft.max_speed_ms,
            drone_fitted=list(aircraft.fitted),
            adjacent_area_populated=adjacent,
        )
    except UnsatisfiableMission as exc:
        raise DeterminationError("The rules engine refused this mission: " + "; ".join(exc.reasons)) from exc

    repo.create_determination(_to_row(determination))
    repo.replace_mitigations(operation_id, intake.mitigation_rows(mission))
    # A determined operation is no longer a draft. Later statuses — dossier ready,
    # submitted, authorised — are set by the actions that earn them, never here.
    operation = repo.get_operation(org_id, operation_id)
    if operation.get("status") == "draft":
        repo.update_operation(org_id, operation_id, {"status": "determined"})
    return determination, True


def latest(repo: Repo, org_id: UUID, operation_id: UUID) -> Determination | None:
    repo.get_operation(org_id, operation_id)  # org scoping
    row = repo.latest_determination(operation_id)
    return Determination.model_validate(_from_row(row)) if row else None


def counterfactuals(
    repo: Repo,
    org_id: UUID,
    operation_id: UUID,
    *,
    target_sail: str | None = None,
    limit: int = 6,
) -> list[Any]:
    mission = confirmed_mission(repo, org_id, operation_id)
    aircraft = _aircraft(repo, org_id, mission.drone_id)
    return suggest(
        mission,
        aircraft,
        target_sail=target_sail,
        adjacent_area_populated=adjacent_area_is_populated(repo, operation_id),
        limit=limit,
    )


def derive_geo(repo: Repo, org_id: UUID, operation_id: UUID) -> dict[str, Any]:
    """Derive the volumes and record what was sampled, so the result is reproducible."""
    operation = repo.get_operation(org_id, operation_id)
    draft = dict(operation.get("mission") or {})
    volume = dict(draft.get("volume") or {})
    if not volume.get("flight_geography"):
        raise DeterminationError("draw the flight geography before deriving the volumes")
    if not draft.get("drone_id"):
        raise DeterminationError("choose an aircraft before deriving the volumes")

    aircraft = _aircraft(repo, org_id, UUID(str(draft["drone_id"])))
    from app.domain import GeoJSONPolygon

    derived = geo.derive(
        GeoJSONPolygon.model_validate(volume["flight_geography"]),
        max_altitude_agl_m=float(volume.get("max_altitude_agl_m") or 0) or 120.0,
        max_speed_ms=aircraft.max_speed_ms,
    )

    volume.update(
        {
            "contingency_volume": derived.contingency_volume.model_dump(),
            "ground_risk_buffer": derived.ground_risk_buffer.model_dump(),
            "adjacent_area_km": round(derived.adjacent_area_m / 1000, 3),
        }
    )
    draft["volume"] = volume
    repo.update_operation(org_id, operation_id, {"mission": draft})

    return {
        "contingency_volume": derived.contingency_volume.model_dump(),
        "ground_risk_buffer": derived.ground_risk_buffer.model_dump(),
        "adjacent_area": derived.adjacent_area.model_dump(),
        "flight_geography_km2": derived.flight_geography_km2,
        "contingency_volume_km2": derived.contingency_volume_km2,
        "ground_risk_buffer_km2": derived.ground_risk_buffer_km2,
        "adjacent_area_km2": derived.adjacent_area_km2,
        "contingency_lateral_m": derived.contingency_lateral_m,
        "contingency_vertical_m": derived.contingency_vertical_m,
        "ground_risk_buffer_m": derived.ground_risk_buffer_m,
        "adjacent_area_m": derived.adjacent_area_m,
        "derivations": [
            {"value_m": d.value_m, "rule": d.rule, "inputs": d.inputs} for d in derived.derivations
        ],
        "unverified": derived.unverified,
    }


def _pinned_rulebase(repo: Repo, org_id: UUID) -> str:
    """The org's pinned rulebase, or the current one.

    Pinning keeps determinations reproducible while an application is open with an
    authority. A pin to a version this build does not carry is an error rather than a
    silent fall-forward: falling forward would change the operator's determination
    behind their back.
    """
    current = rulebase_version_of()
    try:
        org = repo.get_org(org_id)
    except NotFound:
        return current
    pin = org.get("rulebase_pin")
    if not pin:
        return current
    if pin != current:
        raise DeterminationError(
            f"this organisation is pinned to rulebase {pin}, which this build does not "
            f"carry (it has {current}). Change the pin in Settings, or deploy that rulebase."
        )
    return str(pin)


# ------------------------------------------------------------------ row mapping


def _to_row(d: Determination) -> Row:
    payload = d.model_dump(mode="json")
    return {
        "id": payload["id"],
        "operation_id": payload["operation_id"],
        "rulebase_version": payload["rulebase_version"],
        "mission_hash": payload["mission_hash"],
        "igrc": payload["igrc"],
        "final_grc": payload["final_grc"],
        "initial_arc": payload["initial_arc"],
        "residual_arc": payload["residual_arc"],
        "sail": payload["sail"],
        "tmpr": payload["tmpr"],
        "containment": payload["containment"],
        "osos": payload["osos"],
        "trace": payload["trace"],
        "warnings": payload["warnings"],
        "computed_at": payload["computed_at"],
    }


def _from_row(row: Row) -> Row:
    """Strip the computed fields Pydantic will not accept back on construction."""
    out = dict(row)
    for key in ("is_certified_category", "oso_gaps", "is_verified"):
        out.pop(key, None)
    return out
