"""Which mission fields may be proposed, and what each one is called.

This lives in ``app.domain`` — which imports nothing but itself — so that
``services/llm.py`` can read the field list without acquiring an import path to the
database or the engine. "No import path" is transitive, and ``tests/test_boundary.py``
checks it transitively.
"""

from __future__ import annotations

#: Required before a Mission can be assembled. A draft may be missing any of them.
REQUIRED_FIELDS: tuple[str, ...] = (
    "drone_id",
    "operation_type",
    "volume.flight_geography",
    "volume.max_altitude_agl_m",
    "ground_environment",
    "airspace_class",
)

#: The only fields extraction may propose. Anything outside this set is rejected on the
#: way in, so a model cannot invent a field name and have it shown as a wizard field.
PROPOSABLE_FIELDS: frozenset[str] = frozenset(
    {
        "drone_id",
        "operation_type",
        "volume.max_altitude_agl_m",
        "volume.flight_geography",
        "ground_environment",
        "population_density_per_km2",
        "airspace_class",
        "near_aerodrome",
        "controlled_airspace",
        "atypical_airspace",
        "transponder_mandatory_zone",
        "demonstrated_air_density_rating",
        "adjacent_area_density_per_km2",
        "adjacent_assembly_size",
        "sheltering_applicable",
        "country",
        "mitigations.m1_strategic",
        "mitigations.m1_operational",
        "mitigations.m1_ers",
        "mitigations.m2_impact",
        "mitigations.strategic_air",
        "mitigations.tactical_air",
    }
)

#: Human labels, so an unconfirmed-field list reads like the wizard rather than like JSON.
FIELD_LABELS: dict[str, str] = {
    "drone_id": "Aircraft",
    "operation_type": "Operation type",
    "volume.flight_geography": "Flight geography",
    "volume.max_altitude_agl_m": "Maximum altitude",
    "ground_environment": "Ground environment",
    "population_density_per_km2": "Population density",
    "airspace_class": "Airspace class",
    "near_aerodrome": "Aerodrome environment",
    "controlled_airspace": "Controlled airspace",
    "atypical_airspace": "Atypical airspace",
    "transponder_mandatory_zone": "Mode-S Veil or transponder mandatory zone",
    "demonstrated_air_density_rating": "Demonstrated local air traffic density",
    "adjacent_area_density_per_km2": "Adjacent area population density",
    "adjacent_assembly_size": "Assemblies within 1 km",
    "sheltering_applicable": "Sheltering in the adjacent area",
    "country": "Country",
    "mitigations.m1_strategic": "M1(A) sheltering",
    "mitigations.m1_operational": "M1(B) operational restrictions",
    "mitigations.m1_ers": "M1(C) ground observation",
    "mitigations.m2_impact": "M2 impact dynamics reduced",
    "mitigations.strategic_air": "Strategic air risk mitigation",
    "mitigations.tactical_air": "Tactical air risk mitigation",
}

#: Which wizard step owns each field, so rejecting a fact can return the operator there.
OWNING_STEP: dict[str, str] = {
    "drone_id": "aircraft",
    "operation_type": "operation",
    "volume.max_altitude_agl_m": "operation",
    "volume.flight_geography": "map",
    "ground_environment": "ground",
    "population_density_per_km2": "ground",
    "airspace_class": "airspace",
    "near_aerodrome": "airspace",
    "controlled_airspace": "airspace",
    "atypical_airspace": "airspace",
    "transponder_mandatory_zone": "airspace",
    "demonstrated_air_density_rating": "mitigations",
    "adjacent_area_density_per_km2": "ground",
    "adjacent_assembly_size": "ground",
    "sheltering_applicable": "ground",
    "country": "airspace",
}


def label(field: str) -> str:
    return FIELD_LABELS.get(field, field)


def owning_step(field: str) -> str:
    if field in OWNING_STEP:
        return OWNING_STEP[field]
    return "mitigations" if field.startswith("mitigations.") else "review"
