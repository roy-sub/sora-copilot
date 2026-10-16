"""Wizard state, proposed facts, and the gate in front of the engine.

A ``Mission`` is assembled only from values the operator has confirmed. Facts the
language model proposed sit in ``proposed_facts`` with ``status = pending`` and are
**inert**: this module reads confirmed facts and nothing else, and ``POST /determine``
returns 409 listing what is still unconfirmed rather than running on a partial mission.

That gate is the product. Everything else here is bookkeeping around it.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from pydantic import ValidationError

from app.db.repo import Repo, Row
from app.domain import GeoJSONPolygon, Mission, MitigationClaim, OperationalVolume
from app.domain.common import MitigationKind, Robustness, altitude_band_of
from app.domain.fields import (
    PROPOSABLE_FIELDS,
    REQUIRED_FIELDS,
    label,
)


class IntakeError(ValueError):
    """The draft cannot be used. Never raised for a merely incomplete draft."""


class UnconfirmedFacts(IntakeError):
    """The mission has pending facts. ``fields`` lists them, in the operator's words."""

    def __init__(self, fields: list[str]) -> None:
        super().__init__("facts are waiting for confirmation: " + ", ".join(fields))
        self.fields = fields


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cursor = target
    for part in parts[:-1]:
        nxt = cursor.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[part] = nxt
        cursor = nxt
    cursor[parts[-1]] = value


def _get_path(source: dict[str, Any], path: str) -> Any:
    cursor: Any = source
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def validate_proposals(facts: list[Row]) -> list[Row]:
    """Reject anything the model is not allowed to propose, before it is stored.

    A proposal for an unknown field would be inert anyway, but storing it would put text
    the model invented in front of the operator as if it were a real wizard field.
    """
    out: list[Row] = []
    for fact in facts:
        field = str(fact.get("field", ""))
        base = ".".join(field.split(".")[:2]) if field.startswith("mitigations.") else field
        if base not in PROPOSABLE_FIELDS:
            raise IntakeError(f"{field!r} is not a field the intake model may propose")
        confidence = fact.get("confidence")
        if confidence is None or not (0 <= float(confidence) <= 1):
            raise IntakeError(f"{field!r} was proposed without a confidence between 0 and 1")
        out.append(fact)
    return out


def apply_confirmed(draft: Row, facts: list[Row]) -> Row:
    """Fold confirmed facts into the draft. Pending and rejected facts are ignored."""
    merged: dict[str, Any] = dict(draft)
    for fact in facts:
        if fact.get("status") != "confirmed":
            continue
        _set_path(merged, str(fact["field"]), fact["value"])
    return merged


def unconfirmed_fields(facts: list[Row]) -> list[str]:
    """Pending facts, as labels. The 409 body is built from this."""
    return [label(str(f["field"])) for f in facts if f.get("status") == "pending"]


def missing_fields(draft: Row) -> list[str]:
    """Required fields the draft does not yet carry, as labels."""
    return [label(f) for f in REQUIRED_FIELDS if _get_path(draft, f) in (None, "", [], {})]


def build_mission(
    *,
    operation: Row,
    confirmed_draft: Row,
    org_id: UUID,
) -> Mission:
    """Assemble a validated Mission from a complete, confirmed draft.

    Raises ``IntakeError`` with a readable list rather than a Pydantic dump: the operator
    sees this message when a determination will not run.
    """
    missing = missing_fields(confirmed_draft)
    if missing:
        raise IntakeError("the mission is incomplete: " + ", ".join(missing))

    volume_raw = dict(confirmed_draft.get("volume") or {})
    try:
        flight_geography = GeoJSONPolygon.model_validate(volume_raw["flight_geography"])
    except (KeyError, ValidationError) as exc:
        raise IntakeError("the flight geography is missing or not a valid GeoJSON polygon") from exc

    volume_update: dict[str, Any] = {
        "flight_geography": flight_geography,
        "max_altitude_agl_m": float(volume_raw["max_altitude_agl_m"]),
    }
    for key in ("contingency_volume", "ground_risk_buffer"):
        if volume_raw.get(key):
            volume_update[key] = GeoJSONPolygon.model_validate(volume_raw[key])
    if volume_raw.get("adjacent_area_km") is not None:
        volume_update["adjacent_area_km"] = float(volume_raw["adjacent_area_km"])

    mitigations_raw = confirmed_draft.get("mitigations") or {}
    claims: list[MitigationClaim] = []
    if isinstance(mitigations_raw, dict):
        for kind, value in mitigations_raw.items():
            claim = _claim(kind, value)
            if claim is not None:
                claims.append(claim)
    elif isinstance(mitigations_raw, list):
        for item in mitigations_raw:
            claims.append(MitigationClaim.model_validate(item))

    altitude = float(volume_raw["max_altitude_agl_m"])
    try:
        return Mission(
            id=UUID(str(operation["id"])),
            org_id=org_id,
            drone_id=UUID(str(confirmed_draft["drone_id"])),
            operation_type=confirmed_draft["operation_type"],
            volume=OperationalVolume.model_validate(volume_update),
            ground_environment=confirmed_draft["ground_environment"],
            population_density_per_km2=confirmed_draft.get("population_density_per_km2"),
            airspace_class=confirmed_draft["airspace_class"],
            near_aerodrome=bool(confirmed_draft.get("near_aerodrome", False)),
            # Derived from the altitude against the transcribed 150 m threshold, never
            # taken from the draft: the engine computes the band itself and the mission
            # must not be able to disagree with it.
            altitude_band=altitude_band_of(altitude),
            controlled_airspace=bool(confirmed_draft.get("controlled_airspace", False)),
            atypical_airspace=bool(confirmed_draft.get("atypical_airspace", False)),
            transponder_mandatory_zone=bool(
                confirmed_draft.get("transponder_mandatory_zone", False)
            ),
            demonstrated_air_density_rating=confirmed_draft.get(
                "demonstrated_air_density_rating"
            ),
            adjacent_area_density_per_km2=confirmed_draft.get(
                "adjacent_area_density_per_km2"
            ),
            adjacent_assembly_size=confirmed_draft.get("adjacent_assembly_size"),
            sheltering_applicable=confirmed_draft.get("sheltering_applicable"),
            mitigations=claims,
            country=confirmed_draft.get("country", "AT"),
        )
    except ValidationError as exc:
        details = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
        raise IntakeError(f"the mission is not valid: {details}") from exc


def _claim(kind: str, value: Any) -> MitigationClaim | None:
    """One mitigation from the draft's ``{kind: level}`` or ``{kind: {...}}`` shape."""
    if value in (None, "", "none", Robustness.NONE):
        return None
    if isinstance(value, dict):
        return MitigationClaim.model_validate({"kind": kind, **value})
    return MitigationClaim(kind=cast("MitigationKind", kind), robustness=Robustness(value))


def mitigation_rows(mission: Mission) -> list[Row]:
    """The mitigations table as a projection of the mission, which stays authoritative."""
    return [
        {
            "kind": m.kind,
            "robustness": m.robustness.value,
            "evidence_status": m.evidence_status,
            "notes": m.notes,
        }
        for m in mission.mitigations
    ]


def save_draft(repo: Repo, org_id: UUID, operation_id: UUID, patch: Row) -> Row:
    """Merge a wizard patch into the operation's draft mission.

    Shallow-merges one level into ``volume`` and ``mitigations`` so a step can save its
    own fields without resending the whole mission.

    A value of ``None`` **deletes** the field rather than storing a null, at either
    level, which is what lets the wizard withdraw an answer. The engine reads absence as
    "not established" — no demonstrated air traffic density means no Table C.2
    reduction, no adjacent-area measurement means Step #8 asks for an assessment — so a
    field that cannot be cleared is a claim the operator cannot take back.
    """
    operation = repo.get_operation(org_id, operation_id)
    draft: dict[str, Any] = dict(operation.get("mission") or {})
    for key, value in patch.items():
        if key in ("volume", "mitigations") and isinstance(value, dict):
            existing = dict(draft.get(key) or {})
            for inner, inner_value in value.items():
                if inner_value is None:
                    existing.pop(inner, None)
                else:
                    existing[inner] = inner_value
            draft[key] = existing
        elif value is None:
            draft.pop(key, None)
        else:
            draft[key] = value
    return repo.update_operation(org_id, operation_id, {"mission": draft})
