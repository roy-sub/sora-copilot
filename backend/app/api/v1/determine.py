"""Run the determination, read the latest one, and search counterfactuals.

``POST /determine`` returns **409** with the unconfirmed fields rather than running on a
partial mission. That is not a convenience check — it is the only thing standing between
a proposed fact and a regulatory conclusion.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.deps_api import RepoDep, not_found
from app.api.v1.gate import GateDep
from app.api.v1.schemas import (
    ApplyCounterfactualIn,
    CounterfactualIn,
    CounterfactualOut,
    DeterminationOut,
    DraftOut,
)
from app.db.repo import NotFound
from app.deps import OrgContextDep
from app.domain import Determination
from app.problem import ProblemError, UnconfirmedFacts
from app.services import determination as service
from app.services import intake

router = APIRouter(prefix="/operations", tags=["determination"])


def _out(d: Determination, fresh: bool) -> DeterminationOut:
    payload = d.model_dump(mode="json")
    return DeterminationOut.model_validate({**payload, "freshly_computed": fresh})


def _translate(exc: Exception) -> ProblemError:
    if isinstance(exc, intake.UnconfirmedFacts):
        return UnconfirmedFacts(exc.fields)
    if isinstance(exc, intake.IntakeError):
        return ProblemError(
            code="mission_incomplete",
            title="The mission is not complete",
            status_code=409,
            detail=str(exc),
        )
    if isinstance(exc, service.DeterminationError):
        return ProblemError(
            code="determination_refused",
            title="The determination could not be computed",
            status_code=422,
            detail=str(exc),
        )
    raise exc


@router.post(
    "/{operation_id}/determine",
    response_model=DeterminationOut,
    summary="Compute the determination from confirmed facts only",
)
def run(
    operation_id: UUID,
    ctx: OrgContextDep,
    repo: RepoDep,
    gate: GateDep,
    force: bool = False,
) -> DeterminationOut:
    try:
        repo.get_operation(ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc
    # Before the run, not after: an engine run costs real CPU on a free-tier instance, so
    # the limit has to be a refusal rather than a receipt. After the ownership check, so a
    # 402 cannot confirm another operator's operation.
    gate.require_count("determinations")

    try:
        determination, fresh = service.run(repo, ctx.org_id, operation_id, force=force)
    except NotFound as exc:
        raise not_found("operation") from exc
    except (intake.IntakeError, service.DeterminationError) as exc:
        raise _translate(exc) from exc
    return _out(determination, fresh)


@router.get("/{operation_id}/determination", response_model=DeterminationOut)
def latest(operation_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> DeterminationOut:
    try:
        determination = service.latest(repo, ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc
    if determination is None:
        raise ProblemError(
            code="no_determination",
            title="This operation has not been run yet",
            status_code=404,
            detail="Complete the wizard and run the determination.",
        )
    return _out(determination, False)


@router.post("/{operation_id}/counterfactual", response_model=CounterfactualOut)
def counterfactual(
    operation_id: UUID,
    body: CounterfactualIn,
    ctx: OrgContextDep,
    repo: RepoDep,
    gate: GateDep,
) -> CounterfactualOut:
    """Minimal change sets that lower SAIL. Every one is re-run by the engine."""
    try:
        repo.get_operation(ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc
    gate.require_feature("counterfactuals")

    try:
        current = service.latest(repo, ctx.org_id, operation_id)
        suggestions = service.counterfactuals(
            repo,
            ctx.org_id,
            operation_id,
            target_sail=body.target_sail.value if body.target_sail else None,
            limit=body.limit,
        )
    except NotFound as exc:
        raise not_found("operation") from exc
    except (intake.IntakeError, service.DeterminationError) as exc:
        raise _translate(exc) from exc

    if current is None:
        raise ProblemError(
            code="no_determination",
            title="Run the determination first",
            status_code=409,
            detail="Counterfactuals are measured against a determination that exists.",
        )
    return CounterfactualOut(suggestions=suggestions, current_sail=current.sail)


@router.post(
    "/{operation_id}/counterfactual/apply",
    response_model=DraftOut,
    summary="Apply a suggestion to the draft — it does NOT run the determination",
)
def apply_counterfactual(
    operation_id: UUID,
    body: ApplyCounterfactualIn,
    ctx: OrgContextDep,
    repo: RepoDep,
) -> DraftOut:
    """Write the suggested values into the draft and leave it there.

    Applying deliberately does not re-run: the operator sees the change land in the
    wizard, in the step that owns it, and runs the determination themselves. A suggestion
    that silently became a determination would blur the line the whole product defends.
    """
    try:
        suggestions = service.counterfactuals(repo, ctx.org_id, operation_id, limit=50)
    except NotFound as exc:
        raise not_found("operation") from exc
    except (intake.IntakeError, service.DeterminationError) as exc:
        raise _translate(exc) from exc

    match = next((s for s in suggestions if s.id == body.suggestion_id), None)
    if match is None:
        raise ProblemError(
            code="suggestion_stale",
            title="That suggestion is no longer available",
            status_code=409,
            detail=(
                "The mission changed since the suggestion was offered. Ask for the counterfactuals again."
            ),
        )

    patch: dict[str, object] = {}
    mitigations: dict[str, object] = {}
    for change in match.changes:
        if change.field.startswith("mitigations."):
            mitigations[change.field.split(".", 1)[1]] = change.to_value
        elif change.field == "volume":
            patch.setdefault("volume", {})
            assert isinstance(patch["volume"], dict)
            patch["volume"]["max_altitude_agl_m"] = change.to_value
        elif change.field == "near_aerodrome":
            patch["near_aerodrome"] = change.to_value
        elif change.field == "ground_environment":
            patch["ground_environment"] = change.to_value
        elif change.field == "operation_type":
            patch["operation_type"] = change.to_value
    if mitigations:
        patch["mitigations"] = mitigations

    intake.save_draft(repo, ctx.org_id, operation_id, patch)
    from app.api.v1.operations import _draft_out

    return _draft_out(repo, ctx.org_id, operation_id)
