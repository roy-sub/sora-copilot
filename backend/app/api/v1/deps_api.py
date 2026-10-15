"""Shared API dependencies: the repository, and the problem translation for NotFound."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.db import get_repo as _get_repo
from app.db.repo import NotFound, Repo, Row
from app.deps import OrgContextDep
from app.problem import ProblemError


def repo() -> Repo:
    return _get_repo()


RepoDep = Annotated[Repo, Depends(repo)]


def not_found(what: str) -> ProblemError:
    """One message whether the row is absent or belongs to another organisation.

    Distinguishing the two would leak the existence of other operators' operations.
    """
    return ProblemError(
        code="not_found",
        title=f"That {what} is not available",
        status_code=404,
        detail=f"No {what} with that id exists in your organisation.",
    )


def own_operation(repo: Repo, ctx: OrgContextDep, operation_id: UUID) -> Row:
    try:
        return repo.get_operation(ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc
