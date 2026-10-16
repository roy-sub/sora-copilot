"""Mission → ASP ground atoms.

This module does not interpret anything. It converts a confirmed ``Mission`` into facts
in the operator's own vocabulary and hands them to the solver; every judgement about what
those facts mean lives in the ``.lp`` rules, where a reviewer can read it against the
regulation.

Scaling to integers goes through ``app.engine.scale`` so the renderer and the table
generator cannot disagree.
"""

from __future__ import annotations

from app.domain import Mission
from app.domain.common import GroundEnvironment
from app.engine.scale import density_to_int, kg_to_g, m_to_cm, ms_to_cms

#: Mitigation kinds the rulebase reasons about, in the order Table 5 applies them —
#: M1(A), M1(B), M1(C), then M2 — because S.4.3.3(a) says they are applied in numerical
#: sequence, and the trace reads in the same order.
MITIGATION_KINDS = (
    "m1_strategic",
    "m1_operational",
    "m1_ers",
    "m2_impact",
    "strategic_air",
    "tactical_air",
)


class FactError(ValueError):
    """A mission cannot be rendered. Raised rather than rendering a partial fact set."""


def _quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(
    mission: Mission,
    *,
    drone_max_dimension_m: float,
    drone_mtom_kg: float,
    drone_max_speed_ms: float,
    drone_fitted: list[str] | None = None,
    adjacent_area_populated: bool = False,
) -> str:
    """The mission as ASP facts.

    The aircraft's dimensions are passed in rather than read from the mission, because a
    ``Mission`` references a drone by id and this module may not reach the database.
    The caller — ``services/determination.py`` — loads the drone and supplies them.
    """
    density = mission.population_density_per_km2
    if (
        mission.ground_environment not in (GroundEnvironment.CONTROLLED, GroundEnvironment.ASSEMBLY)
        and density is None
    ):
        raise FactError(
            "population_density_per_km2 is required unless the ground environment is a "
            "controlled ground area or an assembly of people, because the iGRC row is "
            "the density band."
        )

    lines: list[str] = [
        "%% Mission facts. Rendered by app/engine/facts.py — not hand-written.",
        "",
        f"operation_type({mission.operation_type.value}).",
        f"ground_env({mission.ground_environment.value}).",
        f"airspace_class({mission.airspace_class.value}).",
        f"country({mission.country.value.lower()}).",
        "",
        f"dim_cm({m_to_cm(drone_max_dimension_m)}).",
        f"speed_cms({ms_to_cms(drone_max_speed_ms)}).",
        f"mtom_g({kg_to_g(drone_mtom_kg)}).",
        f"alt_cm({m_to_cm(mission.volume.max_altitude_agl_m)}).",
    ]

    # A controlled ground area and an assembly of people select the iGRC row directly, so
    # a density is not required; when one was sampled it is still recorded, because the
    # dossier states what was measured.
    if density is not None:
        lines.append(f"density({density_to_int(density)}).")

    lines.append("")
    if mission.controlled_airspace:
        lines.append("controlled_airspace.")
    if mission.near_aerodrome:
        lines.append("near_aerodrome.")
    if mission.atypical_airspace:
        lines.append("atypical_airspace.")
    if mission.transponder_mandatory_zone:
        lines.append("transponder_mandatory_zone.")
    if adjacent_area_populated:
        lines.append("adjacent_area_populated.")

    # Step #4: Table C.2 trades a lower residual ARC for a demonstrated local density.
    # Absent the demonstration there is no row and the residual ARC equals the initial.
    if mission.demonstrated_air_density_rating is not None:
        lines.append(f"demonstrated_air_density({mission.demonstrated_air_density_rating}).")

    # Step #8: the two column inputs for Tables 8 to 13, and the sheltering question
    # that only a 3 m UA is asked.
    if mission.adjacent_area_density_per_km2 is not None:
        lines.append(
            f"adjacent_density({density_to_int(mission.adjacent_area_density_per_km2)})."
        )
    if mission.adjacent_assembly_size is not None:
        # Quoted: "40k_to_400k" starts with a digit and is not a valid ASP
        # constant, and a band that parses only for three of its four values is
        # the kind of thing that works until the day it does not.
        lines.append(f'adjacent_assembly("{mission.adjacent_assembly_size}").')
    if mission.sheltering_applicable is not None:
        lines.append(f"sheltering({'true' if mission.sheltering_applicable else 'false'}).")

    lines.append("")
    for item in drone_fitted or []:
        lines.append(f"fitted({item}).")

    lines.append("")
    for kind in MITIGATION_KINDS:
        claim = mission.mitigation(kind)  # type: ignore[arg-type]
        level = claim.robustness.value if claim else "none"
        lines.append(f"mitigation({kind}, {level}).")

    return "\n".join(lines) + "\n"


def mission_summary(mission: Mission) -> dict[str, str]:
    """Human-readable fact leaves for the trace, in the operator's vocabulary."""
    env = {
        "controlled_ground_area": "controlled ground area",
        "sparsely_populated": "sparsely populated",
        "populated": "populated",
        "assembly_of_people": "assembly of people",
    }[mission.ground_environment.value]
    out = {
        "operation_type": mission.operation_type.value.upper(),
        "ground_environment": env,
        "airspace_class": f"Class {mission.airspace_class.value.upper()}",
        "max_altitude": f"{mission.volume.max_altitude_agl_m:g} m AGL",
        "country": mission.country.value,
    }
    if mission.population_density_per_km2 is not None:
        out["population_density"] = f"{mission.population_density_per_km2:,.0f} ppl/km²"
    return out
