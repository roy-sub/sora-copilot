"""Operations, the wizard draft, and fact confirmation.

The confirm and reject endpoints are the data-flow gate from the architecture: they are
the only way a proposed fact stops being pending, and the determination service reads
nothing else.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.v1.deps_api import RepoDep, not_found
from app.api.v1.schemas import (
    DraftOut,
    MissionDraftPatch,
    OperationIn,
    OperationOut,
    OperationPatch,
    ProposedFactOut,
)
from app.db.repo import NotFound, Repo, Row
from app.deps import CurrentUserDep, OrgContextDep
from app.domain.fields import label, owning_step
from app.problem import ProblemError  # noqa: F401  — re-exported for routers
from app.services import intake

router = APIRouter(prefix="/operations", tags=["operations"])

def _fact_out(row: Row) -> ProposedFactOut:
    field = str(row["field"])
    return ProposedFactOut(
        id=row["id"],
        field=field,
        label=label(field),
        value=row["value"],
        confidence=row["confidence"],
        source_span=row.get("source_span"),
        status=row["status"],
        owning_step=owning_step(field),
    )


def _gaps(determination: Row | None) -> int | None:
    """Required OSOs with no evidence yet. None when nothing has been determined."""
    if determination is None:
        return None
    return sum(
        1
        for o in determination["osos"]
        if o.get("required_robustness") != "none" and o.get("status") == "unmet"
    )


def _operation_out(repo: Repo, row: Row) -> OperationOut:
    """One dashboard row: the operation plus whatever the engine has concluded about it."""
    operation_id = UUID(str(row["id"]))
    determination = repo.latest_determination(operation_id)
    facts = repo.list_facts(operation_id)
    return OperationOut(
        id=row["id"],
        name=row["name"],
        site=row.get("site"),
        status=row.get("status", "draft"),
        drone_id=row.get("drone_id") or (row.get("mission") or {}).get("drone_id"),
        mission=row.get("mission") or {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        sail=determination["sail"] if determination else None,
        rulebase_version=determination["rulebase_version"] if determination else None,
        determined_at=determination["computed_at"] if determination else None,
        oso_gaps=(
            sum(
                1
                for o in determination["osos"]
                if o.get("required_robustness") != "none" and o.get("status") == "unmet"
            )
            if determination
            else None
        ),
        unconfirmed_facts=sum(1 for f in facts if f["status"] == "pending"),
    )


@router.get("", response_model=list[OperationOut])
def list_operations(ctx: OrgContextDep, repo: RepoDep) -> list[OperationOut]:
    return [_operation_out(repo, r) for r in repo.list_operations(ctx.org_id)]


@router.post("", response_model=OperationOut, status_code=status.HTTP_201_CREATED)
def create_operation(body: OperationIn, ctx: OrgContextDep, repo: RepoDep) -> OperationOut:
    mission: dict[str, object] = {}
    if body.drone_id is not None:
        try:
            repo.get_drone(ctx.org_id, body.drone_id)
        except NotFound as exc:
            raise not_found("aircraft") from exc
        mission["drone_id"] = str(body.drone_id)
    row = repo.create_operation(
        ctx.org_id,
        {
            "name": body.name,
            "site": body.site,
            "drone_id": str(body.drone_id) if body.drone_id else None,
            "mission": mission,
        },
    )
    return _operation_out(repo, row)


@router.get("/{operation_id}", response_model=OperationOut)
def get_operation(operation_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> OperationOut:
    try:
        return _operation_out(repo, repo.get_operation(ctx.org_id, operation_id))
    except NotFound as exc:
        raise not_found("operation") from exc


@router.patch("/{operation_id}", response_model=OperationOut)
def update_operation(
    operation_id: UUID, body: OperationPatch, ctx: OrgContextDep, repo: RepoDep
) -> OperationOut:
    try:
        row = repo.update_operation(ctx.org_id, operation_id, body.model_dump(exclude_none=True))
    except NotFound as exc:
        raise not_found("operation") from exc
    return _operation_out(repo, row)


@router.delete("/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_operation(operation_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> None:
    try:
        repo.delete_operation(ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc


# ------------------------------------------------------------------ the draft


def _draft_out(repo: Repo, org_id: UUID, operation_id: UUID) -> DraftOut:
    operation = repo.get_operation(org_id, operation_id)
    facts = repo.list_facts(operation_id)
    confirmed = intake.apply_confirmed(dict(operation.get("mission") or {}), facts)
    missing = intake.missing_fields(confirmed)
    pending = intake.unconfirmed_fields(facts)
    return DraftOut(
        operation_id=operation_id,
        mission=confirmed,
        missing_fields=missing,
        unconfirmed_fields=pending,
        ready_to_determine=not missing and not pending,
    )


@router.get("/{operation_id}/draft", response_model=DraftOut, tags=["intake"])
def get_draft(operation_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> DraftOut:
    try:
        return _draft_out(repo, ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc


@router.patch("/{operation_id}/draft", response_model=DraftOut, tags=["intake"])
def patch_draft(operation_id: UUID, body: MissionDraftPatch, ctx: OrgContextDep, repo: RepoDep) -> DraftOut:
    """Save one wizard step. Nothing here reaches the engine."""
    patch = body.model_dump(exclude_none=True, mode="json")
    if body.drone_id is not None:
        try:
            repo.get_drone(ctx.org_id, body.drone_id)
        except NotFound as exc:
            raise not_found("aircraft") from exc
    try:
        intake.save_draft(repo, ctx.org_id, operation_id, patch)
        return _draft_out(repo, ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc


# ------------------------------------------------------------------ facts


@router.get("/{operation_id}/facts", response_model=list[ProposedFactOut], tags=["intake"])
def list_facts(operation_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> list[ProposedFactOut]:
    try:
        repo.get_operation(ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc
    return [_fact_out(f) for f in repo.list_facts(operation_id)]


@router.post(
    "/{operation_id}/facts/{fact_id}/confirm",
    response_model=ProposedFactOut,
    tags=["intake"],
    summary="Confirm a proposed fact — the only way one reaches the engine",
)
def confirm_fact(
    operation_id: UUID,
    fact_id: UUID,
    ctx: OrgContextDep,
    user: CurrentUserDep,
    repo: RepoDep,
) -> ProposedFactOut:
    """An explicit operator action. There is no other path from pending to confirmed."""
    try:
        repo.get_operation(ctx.org_id, operation_id)
        row = repo.set_fact_status(operation_id, fact_id, "confirmed", user.id)
    except NotFound as exc:
        raise not_found("fact") from exc
    # A confirmed fact becomes part of the draft, so the wizard shows it in its step.
    intake.save_draft(repo, ctx.org_id, operation_id, _as_patch(row))
    return _fact_out(row)


@router.post(
    "/{operation_id}/facts/{fact_id}/reject",
    response_model=ProposedFactOut,
    tags=["intake"],
)
def reject_fact(
    operation_id: UUID,
    fact_id: UUID,
    ctx: OrgContextDep,
    user: CurrentUserDep,
    repo: RepoDep,
) -> ProposedFactOut:
    """A rejected fact is kept, struck through, and never read again."""
    try:
        repo.get_operation(ctx.org_id, operation_id)
        row = repo.set_fact_status(operation_id, fact_id, "rejected", user.id)
    except NotFound as exc:
        raise not_found("fact") from exc
    return _fact_out(row)


def _as_patch(fact: Row) -> dict[str, object]:
    """A confirmed fact as a draft patch, nesting dotted paths one level."""
    field = str(fact["field"])
    if "." in field:
        head, tail = field.split(".", 1)
        return {head: {tail: fact["value"]}}
    return {field: fact["value"]}
