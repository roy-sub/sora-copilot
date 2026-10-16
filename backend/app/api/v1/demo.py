"""The worked example: one endpoint that builds a complete, computed operation.

Not a fixture and not a separate code path — the seeder assembles a mission and runs it
through the same engine every determination goes through, into the caller's own
organisation. See ``app/services/demo.py`` for why that matters.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.v1.deps_api import RepoDep
from app.api.v1.gate import GateDep
from app.api.v1.operations import _operation_out
from app.api.v1.schemas import OperationOut
from app.deps import OrgContextDep
from app.problem import ProblemError
from app.services import demo

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get(
    "/example",
    response_model=OperationOut | None,
    summary="The worked example for this organisation, if it has one",
)
def example(ctx: OrgContextDep, repo: RepoDep) -> OperationOut | None:
    row = demo.existing(repo, ctx.org_id)
    return _operation_out(repo, row) if row is not None else None


@router.post(
    "/example",
    response_model=OperationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Build a complete worked example and run it",
)
def seed(ctx: OrgContextDep, repo: RepoDep, gate: GateDep, response: Response) -> OperationOut:
    """Create the worked example, or return the one this organisation already has.

    It costs an operation and a determination against the plan, exactly as drawing one
    by hand would: a free account that has used its three operations is told so rather
    than being given a fourth through a side door.
    """
    if (already := demo.existing(repo, ctx.org_id)) is not None:
        # 201 would claim something was created. Nothing was, and a client that watches
        # the status to decide whether to announce "example ready" would announce it twice.
        response.status_code = status.HTTP_200_OK
        return _operation_out(repo, already)

    gate.require_count("operations")
    gate.require_count("determinations")

    try:
        row = demo.seed(repo, ctx.org_id)
    except demo.DemoError as exc:
        raise ProblemError(
            code="demo_unavailable",
            title="The worked example could not be built",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return _operation_out(repo, row)
