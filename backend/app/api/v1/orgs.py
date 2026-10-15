"""Organisation and session."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.deps_api import RepoDep
from app.api.v1.schemas import OrgOut, OrgPatch
from app.db.repo import NotFound, Repo
from app.deps import CurrentUserDep, OrgContextDep
from app.problem import ProblemError

router = APIRouter(tags=["organisation"])


def _out(repo: Repo, org_id: UUID | str, role: str) -> OrgOut:
    org = repo.get_org(org_id)
    return OrgOut(
        id=org["id"],
        name=org["name"],
        country=org.get("country", "AT"),
        plan=org.get("plan", "free"),
        data_region=org.get("data_region", "frankfurt"),
        rulebase_pin=org.get("rulebase_pin"),
        role=role,
        seats_used=len(repo.members(org_id)),
        created_at=org["created_at"],
    )


@router.post("/auth/session", response_model=OrgOut, summary="Exchange a verified token for org context")
def session(user: CurrentUserDep, repo: RepoDep) -> OrgOut:
    """Called once after sign-in.

    Creates the organisation if the user has none. The database trigger normally does
    this on sign-up; doing it here as well means a user whose org was never created — or
    was deleted — is not stranded on a dashboard with nowhere to put an operation.
    """
    member = repo.ensure_org_for_user(user.id, user.email)
    return _out(repo, member["org_id"], member["role"])


@router.get("/orgs/me", response_model=OrgOut)
def me(ctx: OrgContextDep, repo: RepoDep) -> OrgOut:
    try:
        return _out(repo, ctx.org_id, ctx.role)
    except NotFound as exc:
        raise ProblemError(
            code="no_organisation",
            title="This account has no organisation",
            status_code=403,
            detail="Call POST /api/v1/auth/session once after signing in.",
        ) from exc


@router.patch("/orgs/me", response_model=OrgOut)
def update_me(patch: OrgPatch, ctx: OrgContextDep, repo: RepoDep) -> OrgOut:
    if not ctx.can_admin:
        raise ProblemError(
            code="forbidden",
            title="Only an owner or admin can change the organisation",
            status_code=403,
        )
    repo.update_org(ctx.org_id, patch.model_dump(exclude_none=True))
    return _out(repo, ctx.org_id, ctx.role)
