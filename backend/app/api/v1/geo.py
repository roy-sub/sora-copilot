"""Volume derivation and the population density sample.

The operator draws the flight geography; everything else is derived and the derivation
says what produced it. The density sample is always shown for confirmation with an
override, and is recorded with the raster version so a determination stays reproducible.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.deps_api import RepoDep, not_found
from app.api.v1.schemas import DensitySampleIn, DensitySampleOut, GeoDeriveOut
from app.db.repo import NotFound
from app.deps import OrgContextDep
from app.problem import ProblemError
from app.services import determination as service
from app.services import geo, intake

router = APIRouter(prefix="/operations", tags=["geo"])

#: No raster is bundled yet, so a sample is whatever the operator supplied. Recorded
#: honestly rather than labelled with a dataset we are not using.
OPERATOR_SOURCE = "operator-entered"


@router.post(
    "/{operation_id}/geo/derive",
    response_model=GeoDeriveOut,
    summary="Derive the contingency volume, ground risk buffer and adjacent area",
)
def derive(operation_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> GeoDeriveOut:
    try:
        return GeoDeriveOut.model_validate(service.derive_geo(repo, ctx.org_id, operation_id))
    except NotFound as exc:
        raise not_found("operation") from exc
    except geo.GeoError as exc:
        raise ProblemError(
            code="geometry_invalid",
            title="The flight geography cannot be used",
            status_code=422,
            detail=str(exc),
        ) from exc
    except service.DeterminationError as exc:
        raise ProblemError(
            code="geo_incomplete",
            title="Not enough information to derive the volumes",
            status_code=409,
            detail=str(exc),
        ) from exc


@router.post(
    "/{operation_id}/geo/density",
    response_model=DensitySampleOut,
    summary="Record the sampled population density and get a suggested ground environment",
)
def density(operation_id: UUID, body: DensitySampleIn, ctx: OrgContextDep, repo: RepoDep) -> DensitySampleOut:
    """Stores the sample and returns a **suggestion**.

    The suggested ground environment never reaches the engine on its own: it prefills the
    wizard, and the operator confirms or corrects it. A controlled ground area and an
    assembly of people are never suggested at all, because no density figure can
    establish either.
    """
    try:
        repo.get_operation(ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc

    band = geo.band_for(body.density_per_km2)
    environment, rationale = geo.ground_environment_for(body.density_per_km2)
    raster_version = body.source or OPERATOR_SOURCE

    repo.put_geo_facts(
        operation_id,
        {
            "density_per_km2": body.density_per_km2,
            "density_band": band,
            "raster_version": raster_version,
            "adjacent_area_populated": body.adjacent_area_populated,
            "operator_override": body.source == "operator",
            "airspace_snapshot": {},
        },
    )
    # The sampled figure goes into the draft so the review step can show it; the
    # environment does not, because that is the operator's call.
    intake.save_draft(repo, ctx.org_id, operation_id, {"population_density_per_km2": body.density_per_km2})

    return DensitySampleOut(
        density_per_km2=body.density_per_km2,
        density_band=band,
        suggested_environment=environment,
        rationale=rationale,
        raster_version=raster_version,
        adjacent_area_populated=body.adjacent_area_populated,
    )
