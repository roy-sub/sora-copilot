"""Organisation, session, members and invitations.

Seats are the one plan limit that cannot be enforced only at the moment of use: two
people accepting an invitation at the same time would put a five-seat organisation at
six. So a pending invitation **holds a seat** — members plus pending invitations is what
is checked against the plan, not members alone.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, status

from app.api.v1.deps_api import RepoDep
from app.api.v1.gate import GateDep
from app.api.v1.schemas import (
    InviteIn,
    InviteOut,
    MemberOut,
    MemberPatch,
    OrgOut,
    OrgPatch,
    SeatsOut,
)
from app.db.repo import NotFound, Repo, Row
from app.deps import CurrentUserDep, OrgContext, OrgContextDep
from app.problem import ProblemError
from app.services import plans
from app.services.plans import Denial, Plan

#: How long an invitation stays claimable. Mirrors migration 003's column default.
INVITE_DAYS = 14


def _require_admin(ctx: OrgContext) -> None:
    if not ctx.can_admin:
        raise ProblemError(
            code="forbidden",
            title="Only an owner or admin can manage members",
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ask an owner of this organisation to make the change.",
        )


def _plan_refusal(denial: Denial, plan: Plan) -> ProblemError:
    """The same 402 shape the gate produces, for the one limit the gate cannot check."""
    return ProblemError(
        code="plan_limit",
        title=denial.title,
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=denial.detail,
        feature=denial.feature,
        plan=plan.name,
        limit=denial.limit,
        used=denial.used,
        upgrade_to=denial.upgrade_to,
    )

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


# ------------------------------------------------------------------ seats


def _invite_status(row: Row) -> str:
    if row.get("accepted_at"):
        return "accepted"
    expires = str(row.get("expires_at") or "")
    return "expired" if expires and expires < _now_iso() else "pending"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _invite_out(row: Row) -> InviteOut:
    return InviteOut(
        id=row["id"],
        email=str(row["email"]),
        role=row.get("role", "member"),
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        accepted_at=row.get("accepted_at"),
        status=_invite_status(row),
    )


def _seats(repo: Repo, ctx: OrgContextDep, plan: Plan) -> SeatsOut:
    members = repo.members(ctx.org_id)
    invites = repo.list_invites(ctx.org_id)
    pending = [i for i in invites if _invite_status(i) == "pending"]
    committed = len(members) + len(pending)
    return SeatsOut(
        members=[
            MemberOut(
                user_id=m["user_id"],
                email=m.get("email"),
                role=m.get("role", "member"),
                created_at=m["created_at"],
                is_you=str(m["user_id"]) == str(ctx.user.id),
            )
            for m in sorted(members, key=lambda m: str(m["created_at"]))
        ],
        invites=[_invite_out(i) for i in invites],
        seats_used=len(members),
        seats_limit=plan.seats,
        seats_committed=committed,
        can_invite=ctx.can_admin and committed < plan.seats,
        plan=plan.name,
    )


@router.get("/orgs/me/seats", response_model=SeatsOut, summary="Members, invitations and seats")
def seats(ctx: OrgContextDep, repo: RepoDep, gate: GateDep) -> SeatsOut:
    return _seats(repo, ctx, gate.plan)


@router.post(
    "/orgs/me/invites",
    response_model=SeatsOut,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a colleague by email",
)
def invite(body: InviteIn, ctx: OrgContextDep, repo: RepoDep, gate: GateDep) -> SeatsOut:
    """Invite an address to this organisation.

    There is no emailed token link: the invitation is claimed on first sign-in by the
    email in the **verified** Supabase JWT, so only someone who has proved control of
    that address can take it. Tell your colleague to sign up with the address you
    invited. See migration 003 for the reasoning.
    """
    _require_admin(ctx)
    email = str(body.email).strip().lower()

    current = _seats(repo, ctx, gate.plan)
    already = any(m for m in repo.members(ctx.org_id) if str(m.get("email") or "").lower() == email)
    if already:
        raise ProblemError(
            code="already_a_member",
            title="That address is already in this organisation",
            status_code=status.HTTP_409_CONFLICT,
            detail="Nothing to do.",
        )
    # Re-inviting an address that already has a pending invitation updates it rather
    # than taking a second seat, so it is not counted against the limit.
    renewing = any(
        i["email"] == email and _invite_status(i) == "pending" for i in repo.list_invites(ctx.org_id)
    )
    if not renewing and current.seats_committed >= gate.plan.seats:
        denial = plans.check_count("seats", gate.plan, current.seats_committed)
        if denial is not None:
            raise _plan_refusal(denial, gate.plan)

    repo.create_invite(
        ctx.org_id,
        {
            "email": email,
            "role": body.role,
            "invited_by": str(ctx.user.id),
            "expires_at": (datetime.now(UTC) + timedelta(days=INVITE_DAYS)).isoformat(),
        },
    )
    return _seats(repo, ctx, gate.plan)


@router.delete(
    "/orgs/me/invites/{invite_id}",
    response_model=SeatsOut,
    summary="Withdraw an invitation",
)
def revoke_invite(invite_id: UUID, ctx: OrgContextDep, repo: RepoDep, gate: GateDep) -> SeatsOut:
    _require_admin(ctx)
    try:
        repo.delete_invite(ctx.org_id, invite_id)
    except NotFound as exc:
        raise ProblemError(
            code="not_found",
            title="That invitation is not available",
            status_code=status.HTTP_404_NOT_FOUND,
            detail="It may already have been withdrawn or accepted.",
        ) from exc
    return _seats(repo, ctx, gate.plan)


@router.delete(
    "/orgs/me/members/{user_id}",
    response_model=SeatsOut,
    summary="Remove a member",
)
def remove_member(user_id: UUID, ctx: OrgContextDep, repo: RepoDep, gate: GateDep) -> SeatsOut:
    """Remove someone from the organisation.

    Their work stays: operations, determinations and dossiers belong to the organisation,
    not to the person who created them, because a compliance record has to outlive the
    employment that produced it.
    """
    _require_admin(ctx)
    if str(user_id) == str(ctx.user.id):
        raise ProblemError(
            code="cannot_remove_yourself",
            title="You cannot remove yourself",
            status_code=status.HTTP_409_CONFLICT,
            detail="Ask another owner to do it, so an organisation is never left without one.",
        )
    members = repo.members(ctx.org_id)
    target = next((m for m in members if str(m["user_id"]) == str(user_id)), None)
    if target is None:
        raise ProblemError(
            code="not_found",
            title="That member is not available",
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No member with that id is in your organisation.",
        )
    owners = [m for m in members if m.get("role") == "owner"]
    if target.get("role") == "owner" and len(owners) <= 1:
        raise ProblemError(
            code="last_owner",
            title="That is the only owner",
            status_code=status.HTTP_409_CONFLICT,
            detail="Make somebody else an owner first; an organisation without one cannot be managed.",
        )
    repo.remove_member(ctx.org_id, user_id)
    return _seats(repo, ctx, gate.plan)


@router.patch(
    "/orgs/me/members/{user_id}",
    response_model=SeatsOut,
    summary="Change a member's role",
)
def set_role(
    user_id: UUID, body: MemberPatch, ctx: OrgContextDep, repo: RepoDep, gate: GateDep
) -> SeatsOut:
    _require_admin(ctx)
    members = repo.members(ctx.org_id)
    target = next((m for m in members if str(m["user_id"]) == str(user_id)), None)
    if target is None:
        raise ProblemError(
            code="not_found",
            title="That member is not available",
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No member with that id is in your organisation.",
        )
    owners = [m for m in members if m.get("role") == "owner"]
    if target.get("role") == "owner" and body.role != "owner" and len(owners) <= 1:
        raise ProblemError(
            code="last_owner",
            title="That is the only owner",
            status_code=status.HTTP_409_CONFLICT,
            detail="Promote somebody else first; an organisation without an owner cannot be managed.",
        )
    repo.set_member_role(ctx.org_id, user_id, body.role)
    return _seats(repo, ctx, gate.plan)
