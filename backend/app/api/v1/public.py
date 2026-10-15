"""The free category checker. Unauthenticated, rate-limited.

Three questions, answered by the **same engine** the product runs. A typical aircraft is
assumed for the mass band and the assumptions are listed in the response, because an
estimate whose assumptions are hidden is a number with no meaning.

This is the top of the funnel, and it is also the first thing a sceptical compliance
officer will poke at, so it must not overstate what it knows.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, Request

from app.api.v1.schemas import CategoryCheckIn, CategoryCheckOut
from app.domain import GeoJSONPolygon, Mission, OperationalVolume
from app.domain.common import (
    DISCLAIMER,
    AirspaceClass,
    Country,
    GroundEnvironment,
    OperationType,
)
from app.engine.counterfactual import Aircraft, suggest
from app.engine.rulebase.loader import load_rulebase, rulebase_version
from app.engine.runner import UnsatisfiableMission, determine
from app.problem import ProblemError

router = APIRouter(prefix="/public", tags=["public"])

#: A typical aircraft per mass band. Stated in the response, never hidden, because the
#: whole answer depends on them.
TYPICAL: dict[str, tuple[float, float, float, str]] = {
    "sub250": (0.25, 0.249, 19.0, "a 250 g class-C0 multirotor"),
    "c_marked": (0.9, 3.0, 23.0, "a 3 kg class-C2 multirotor"),
    "4to25": (1.5, 15.0, 25.0, "a 15 kg inspection multirotor"),
    "over25": (2.5, 40.0, 30.0, "a 40 kg heavy-lift platform"),
}

#: Density assumed per ground environment, for the checker only.
ASSUMED_DENSITY: dict[str, float | None] = {
    "controlled_ground_area": None,
    "sparsely_populated": 100.0,
    "populated": 1500.0,
    "assembly_of_people": 60000.0,
}

#: A square kilometre near Graz. The checker does not ask for geography, and the volume
#: does not affect the chain, but a Mission needs one.
PLACEHOLDER_GEOGRAPHY = {
    "type": "Polygon",
    "coordinates": [[[15.40, 47.10], [15.41, 47.10], [15.41, 47.11], [15.40, 47.11], [15.40, 47.10]]],
}

# ------------------------------------------------------------------ rate limiting

#: In-process, per-IP. Enough for a free public endpoint on a single instance, and it
#: needs no Redis — which the build spec forbids anyway. A second instance would get its
#: own bucket; that is an accepted limit, not an oversight.
_WINDOW_SECONDS = 60
_MAX_PER_WINDOW = 20
_hits: dict[str, deque[float]] = defaultdict(deque)
_hits_lock = Lock()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit(request: Request) -> None:
    key = _client_key(request)
    now = time.monotonic()
    with _hits_lock:
        bucket = _hits[key]
        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _MAX_PER_WINDOW:
            retry = int(_WINDOW_SECONDS - (now - bucket[0])) + 1
            raise ProblemError(
                code="rate_limited",
                title="Too many checks from this address",
                status_code=429,
                detail=f"Try again in {retry} seconds, or sign in to run full assessments.",
                retry_after=retry,
            )
        bucket.append(now)


# ------------------------------------------------------------------ the check


def _open_category(body: CategoryCheckIn) -> CategoryCheckOut | None:
    """The open category, from EU 2019/947 Art. 4 — not from the SORA tables.

    These are the regulation's own subcategory limits rather than a computed result, so
    they are stated as the reason rather than dressed up as an engine conclusion.
    """
    if body.operation_type is not OperationType.VLOS:
        return None
    if body.mass_band == "over25" or body.ground_environment is GroundEnvironment.ASSEMBLY:
        return None

    common = {
        "category": "open",
        "sail": None,
        "assumptions": _assumptions(body),
        "rulebase_version": rulebase_version(),
        "is_verified": False,
        "disclaimer": DISCLAIMER,
    }
    if body.mass_band == "sub250":
        return CategoryCheckOut(
            subcategory="A1",
            reason=(
                "Under 250 g in visual line of sight may fly over uninvolved people, but "
                "never over an assembly of people."
            ),
            **common,
        )
    if body.mass_band == "c_marked":
        return CategoryCheckOut(
            subcategory="A2",
            reason="A class-marked aircraft up to 4 kg keeps 30 m from uninvolved people.",
            **common,
        )
    if body.ground_environment is not GroundEnvironment.POPULATED:
        return CategoryCheckOut(
            subcategory="A3",
            reason=(
                "Up to 25 kg, far from uninvolved people and at least 150 m from "
                "residential, commercial or industrial areas."
            ),
            **common,
        )
    return None


def _assumptions(body: CategoryCheckIn) -> list[str]:
    dim, mtom, speed, description = TYPICAL[body.mass_band]
    density = ASSUMED_DENSITY[body.ground_environment.value]
    out = [
        f"Aircraft: {description} — {dim:g} m, {mtom:g} kg, {speed:g} m/s maximum speed.",
        "Airspace: class G, uncontrolled, not in an aerodrome environment, not atypical.",
        "Altitude: 120 m AGL, which is below the 500 ft air risk band boundary.",
        "No ground or air risk mitigations claimed.",
    ]
    if density is not None:
        environment = body.ground_environment.value.replace("_", " ")
        out.append(f"Population density: {density:,.0f} ppl/km² for a {environment} environment.")
    return out


def _mission(body: CategoryCheckIn) -> Mission:
    return Mission(
        id=uuid4(),
        org_id=uuid4(),
        drone_id=uuid4(),
        operation_type=body.operation_type,
        volume=OperationalVolume(
            flight_geography=GeoJSONPolygon.model_validate(PLACEHOLDER_GEOGRAPHY),
            max_altitude_agl_m=120.0,
        ),
        ground_environment=body.ground_environment,
        population_density_per_km2=ASSUMED_DENSITY[body.ground_environment.value],
        airspace_class=AirspaceClass.G,
        near_aerodrome=False,
        altitude_band="below_500ft",
        controlled_airspace=False,
        atypical_airspace=False,
        mitigations=[],
        country=Country.EU,
    )


@router.post(
    "/category-check",
    response_model=CategoryCheckOut,
    summary="Open, specific or certified — the same engine, no account",
)
def category_check(body: CategoryCheckIn, request: Request) -> CategoryCheckOut:
    _rate_limit(request)

    if (open_result := _open_category(body)) is not None:
        return open_result

    mission = _mission(body)
    dim, mtom, speed, _ = TYPICAL[body.mass_band]
    aircraft = Aircraft(max_dimension_m=dim, mtom_kg=mtom, max_speed_ms=speed)

    try:
        determination = determine(
            mission,
            drone_max_dimension_m=dim,
            drone_mtom_kg=mtom,
            drone_max_speed_ms=speed,
        )
    except UnsatisfiableMission as exc:
        raise ProblemError(
            code="check_refused",
            title="That combination cannot be assessed",
            status_code=422,
            detail="; ".join(exc.reasons),
        ) from exc

    unverified = sorted(n for n, t in load_rulebase().items() if not t.verified)
    why = _why_not_open(body)

    if determination.is_certified_category:
        return CategoryCheckOut(
            category="certified",
            reason=(
                f"{why} The intrinsic ground risk for this combination is outside SORA, "
                "so it needs the certified category."
            ),
            sail="certified_category",
            igrc=determination.igrc,
            initial_arc=determination.initial_arc,
            assumptions=_assumptions(body),
            rulebase_version=determination.rulebase_version,
            is_verified=not unverified,
            disclaimer=DISCLAIMER,
        )

    best = suggest(mission, aircraft, limit=1)
    hint = None
    if best:
        sail = best[0].resulting_sail
        sail_text = sail if isinstance(sail, str) else sail.value
        hint = f"{best[0].title} would reach SAIL {sail_text} for an operation like this."

    return CategoryCheckOut(
        category="specific",
        reason=f"{why} It needs an operational authorisation in the specific category.",
        sail=determination.sail,
        igrc=determination.igrc,
        initial_arc=determination.initial_arc,
        osos_required=sum(1 for o in determination.osos if o.is_required),
        hint=hint,
        assumptions=_assumptions(body),
        rulebase_version=determination.rulebase_version,
        is_verified=not unverified,
        disclaimer=DISCLAIMER,
    )


def _why_not_open(body: CategoryCheckIn) -> str:
    if body.operation_type is not OperationType.VLOS:
        return f"{body.operation_type.value.upper()} is outside the open category."
    if body.mass_band == "over25":
        return "Over 25 kg is outside the open category."
    if body.ground_environment is GroundEnvironment.ASSEMBLY:
        return "Flight over an assembly of people is outside the open category."
    return "A 4–25 kg aircraft over a populated area is outside subcategory A3."
