"""The fleet."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.v1.deps_api import RepoDep, not_found
from app.api.v1.schemas import DroneIn, DroneOut, DronePatch
from app.db.repo import NotFound, Row
from app.deps import OrgContextDep
from app.problem import ProblemError

router = APIRouter(prefix="/drones", tags=["fleet"])


def _out(row: Row) -> DroneOut:
    return DroneOut.model_validate(row)


@router.get("", response_model=list[DroneOut])
def list_drones(ctx: OrgContextDep, repo: RepoDep) -> list[DroneOut]:
    return [_out(r) for r in repo.list_drones(ctx.org_id)]


@router.post("", response_model=DroneOut, status_code=status.HTTP_201_CREATED)
def create_drone(body: DroneIn, ctx: OrgContextDep, repo: RepoDep) -> DroneOut:
    if body.max_speed_ms < body.cruise_speed_ms:
        raise ProblemError(
            code="validation_failed",
            title="Maximum speed is below cruise speed",
            status_code=422,
            detail="The iGRC column is chosen by maximum speed, so the two cannot be inverted.",
        )
    return _out(repo.create_drone(ctx.org_id, body.model_dump()))


@router.get("/{drone_id}", response_model=DroneOut)
def get_drone(drone_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> DroneOut:
    try:
        return _out(repo.get_drone(ctx.org_id, drone_id))
    except NotFound as exc:
        raise not_found("aircraft") from exc


@router.patch("/{drone_id}", response_model=DroneOut)
def update_drone(drone_id: UUID, body: DronePatch, ctx: OrgContextDep, repo: RepoDep) -> DroneOut:
    try:
        return _out(repo.update_drone(ctx.org_id, drone_id, body.model_dump(exclude_none=True)))
    except NotFound as exc:
        raise not_found("aircraft") from exc


@router.delete("/{drone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_drone(drone_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> None:
    try:
        repo.delete_drone(ctx.org_id, drone_id)
    except NotFound as exc:
        raise not_found("aircraft") from exc
