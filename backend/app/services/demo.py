"""The worked example: a complete operation, seeded on request.

A new account lands on an empty dashboard, and an empty dashboard explains nothing. The
hardest thing to convey about this product is not a feature, it is the *shape* of a
determination — a chain from iGRC to SAIL where every step names the rule that produced
it. That is much easier to show than to describe, so there is a button that builds one.

Three things make this honest rather than a sales fixture:

1. **The determination is computed, not canned.** The seeder assembles a mission and
   hands it to the same engine every other run goes through. If the rulebase changes,
   the worked example changes with it; if the engine cannot justify a conclusion, the
   worked example fails exactly as a real operation would.
2. **It is the operator's own data.** The operation is created in their organisation,
   counts against their plan, and can be edited, re-run and deleted like any other. It
   is a starting point, not a read-only showroom.
3. **It is labelled.** The operation is named and tagged as the worked example, so
   nobody mistakes it for an assessment of a real flight.

The mission below is a plausible Austrian powerline inspection chosen because it lands
mid-scale — SAIL III, with counterfactuals that genuinely reduce it — so the trace, the
OSO matrix and the advisor all have something to show.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.repo import Repo, Row
from app.services import determination as determination_service
from app.services import intake

#: Marks the operation as the seeded example, so it is recognisable in a list and the
#: seeder can refuse to make a second one.
DEMO_TAG = "worked-example"

DEMO_OPERATION_NAME = "Worked example — powerline corridor, Mur valley"

DEMO_DRONE: Row = {
    "name": "Freefly Alta X (worked example)",
    "registration": "DEMO-ALTA-X",
    "max_dimension_m": 1.32,
    "mtom_kg": 15.9,
    "cruise_speed_ms": 18.0,
    "max_speed_ms": 22.0,
    "fitted_mitigations": ["parachute", "fts"],
}

#: A corridor south of Gratkorn, in the Mur valley north of Graz. Roughly 6.7 km².
DEMO_GEOGRAPHY: dict[str, Any] = {
    "type": "Polygon",
    "coordinates": [
        [
            [15.3902, 47.1021],
            [15.4418, 47.1021],
            [15.4418, 47.1194],
            [15.3902, 47.1194],
            [15.3902, 47.1021],
        ]
    ],
}

DEMO_DRAFT: Row = {
    "operation_type": "bvlos",
    "volume": {"flight_geography": DEMO_GEOGRAPHY, "max_altitude_agl_m": 118.0},
    "ground_environment": "sparsely_populated",
    "population_density_per_km2": 84.0,
    "airspace_class": "g",
    "near_aerodrome": True,
    "controlled_airspace": False,
    "atypical_airspace": False,
    "transponder_mandatory_zone": False,
    # Step #5: Annex C Table C.2 does not lower the ARC for a claimed mitigation, only
    # for a demonstrated local traffic density. The example's operator has made that
    # case to Austro Control — AEC 6 at rating 1 — which is what takes the residual ARC
    # from c to b. Without it the same corridor is SAIL IV.
    "demonstrated_air_density_rating": 1,
    # Step #8: the two measurements that select a column in Tables 8 to 13. Farmland
    # with scattered houses beyond the buffer, and no gathering of any size within 1 km
    # of the corridor while the flight is on.
    "adjacent_area_density_per_km2": 310.0,
    "adjacent_assembly_size": "under_40k",
    "sheltering_applicable": True,
    "mitigations": {"m1_strategic": "low", "strategic_air": "low"},
    "country": "AT",
}

#: What the operator would have written in the intake panel. Stored as the operation's
#: description so the example reads like something somebody actually planned.
DEMO_SITE = "Gratkorn — Graz Süd, AT"
DEMO_NOTE = (
    "Annual inspection of the 110 kV line south of Gratkorn. BVLOS along a 5 km "
    "corridor at 118 m AGL over farmland with scattered houses, class G airspace "
    "inside the LOWG aerodrome environment."
)


class DemoError(RuntimeError):
    """The worked example could not be built."""


def existing(repo: Repo, org_id: UUID) -> Row | None:
    """The seeded example, if this organisation already has one."""
    for row in repo.list_operations(org_id):
        mission = row.get("mission") or {}
        if isinstance(mission, dict) and mission.get("demo") is True:
            return row
        if row.get("name") == DEMO_OPERATION_NAME:
            return row
    return None


def seed(repo: Repo, org_id: UUID) -> Row:
    """Build the worked example and run it. Returns the operation.

    Idempotent: an organisation gets one worked example, not one per click. If it is
    deleted, the next call builds a fresh one.
    """
    if (already := existing(repo, org_id)) is not None:
        return already

    drone = _demo_drone(repo, org_id)
    operation = repo.create_operation(
        org_id,
        {
            "name": DEMO_OPERATION_NAME,
            "site": DEMO_SITE,
            "drone_id": str(drone["id"]),
            # `demo: true` rides in the mission so the flag survives any store, and the
            # UI can label the operation without matching on its name.
            "mission": {"drone_id": str(drone["id"]), "demo": True, "note": DEMO_NOTE},
        },
    )
    operation_id = UUID(str(operation["id"]))

    # Through the ordinary draft path, so the example is built the way the wizard builds
    # one — including the validation every field goes through.
    intake.save_draft(repo, org_id, operation_id, {**DEMO_DRAFT, "drone_id": str(drone["id"])})

    # The volumes the engine reads are derived from the drawn geography, never typed.
    try:
        determination_service.derive_geo(repo, org_id, operation_id)
    except Exception as exc:  # surfaced with the real cause rather than swallowed
        raise DemoError(f"the worked example's volumes could not be derived: {exc}") from exc

    try:
        determination_service.run(repo, org_id, operation_id)
    except Exception as exc:  # surfaced with the real cause rather than swallowed
        raise DemoError(
            f"the worked example could not be determined: {exc}. This is the same engine "
            "every operation uses, so it is a real failure, not a demo-only one."
        ) from exc

    return repo.get_operation(org_id, operation_id)


def _demo_drone(repo: Repo, org_id: UUID) -> Row:
    """Reuse the example aircraft if it is already on file, rather than adding a second."""
    for row in repo.list_drones(org_id):
        if row.get("registration") == DEMO_DRONE["registration"]:
            return row
    return repo.create_drone(org_id, dict(DEMO_DRONE))
