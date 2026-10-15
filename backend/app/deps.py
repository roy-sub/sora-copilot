"""Request dependencies: who is calling, and which org they are allowed to act for.

``org_id`` is never read from a request body or query string. It is resolved from
``org_members`` using the ``sub`` of a verified Supabase JWT (build spec §8).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, cast
from uuid import UUID

import jwt
from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.db.client import get_client
from app.problem import ProblemError

_BEARER = "bearer"


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: UUID
    email: str | None
    claims: dict[str, Any]


@dataclass(frozen=True, slots=True)
class OrgContext:
    org_id: UUID
    role: str
    user: CurrentUser

    @property
    def can_admin(self) -> bool:
        return self.role in {"owner", "admin"}


def _unauthenticated(detail: str) -> ProblemError:
    return ProblemError(
        code="unauthenticated", title="Not signed in", status_code=401, detail=detail
    )


def get_current_user(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> CurrentUser:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != _BEARER or not token:
        raise _unauthenticated("Send the Supabase access token as a Bearer header.")
    if not settings.supabase_jwt_secret:
        raise ProblemError(
            code="auth_unconfigured",
            title="Authentication is not configured",
            status_code=503,
            detail="SUPABASE_JWT_SECRET is not set. See .env.example.",
        )

    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"require": ["sub", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthenticated("The session has expired. Sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise _unauthenticated("The access token could not be verified.") from exc

    return CurrentUser(id=UUID(claims["sub"]), email=claims.get("email"), claims=claims)


def get_org_context(user: Annotated[CurrentUser, Depends(get_current_user)]) -> OrgContext:
    rows = (
        get_client()
        .table("org_members")
        .select("org_id, role")
        .eq("user_id", str(user.id))
        .limit(1)
        .execute()
    )
    if not rows.data:
        raise ProblemError(
            code="no_organisation",
            title="This account has no organisation",
            status_code=403,
            detail="Sign in again to have one created, or ask an owner to invite you.",
        )
    # supabase-py types rows as loose JSON; narrow before trusting the shape.
    row = cast("dict[str, Any]", rows.data[0])
    org_id, role = row.get("org_id"), row.get("role")
    if not isinstance(org_id, str) or not isinstance(role, str):
        raise ProblemError(
            code="membership_malformed",
            title="The organisation membership record is unreadable",
            status_code=500,
            detail="org_members returned a row without a usable org_id and role.",
        )
    return OrgContext(org_id=UUID(org_id), role=role, user=user)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
OrgContextDep = Annotated[OrgContext, Depends(get_org_context)]
