"""The country packs, and one operation's submission checklist.

Read-only. Nothing here changes a determination; it narrows an already-computed one to
the administrative file the authority expects. The checklist is tailored by the SAIL the
engine produced and the OSOs it required, never by re-deciding either.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.deps_api import RepoDep, own_operation
from app.api.v1.schemas import (
    NationalCountryOut,
    NationalPackOut,
    PackItemOut,
    SubmissionChecklistOut,
)
from app.deps import OrgContextDep
from app.domain.common import DISCLAIMER
from app.national import PackError, PackItem, available, load_pack, tailor
from app.problem import ProblemError

router = APIRouter(prefix="/national", tags=["national"])


def _item(item: PackItem) -> PackItemOut:
    return PackItemOut(
        id=item.id,
        kind=item.kind,
        title=item.title,
        detail=item.detail,
        min_sail=item.min_sail,
        osos=list(item.osos),
        url=item.url,
        verified=item.verified,
        source=item.source,
    )


def _unknown(country: str) -> ProblemError:
    known = ", ".join(p.country for p in available())
    return ProblemError(
        code="country_unsupported",
        title="There is no pack for that country",
        status_code=404,
        detail=f"{country!r} has no national pack. Available: {known}.",
    )


@router.get("", response_model=list[NationalCountryOut], summary="Countries with a national pack")
def countries() -> list[NationalCountryOut]:
    return [
        NationalCountryOut(
            country=pack.country,
            country_name=pack.country_name,
            authority=pack.authority,
            complete=pack.complete,
            items=len(pack.items),
            unverified=len(pack.unverified_ids),
        )
        for pack in available()
    ]


@router.get("/{country}", response_model=NationalPackOut, summary="One country's process pack")
def pack(country: str) -> NationalPackOut:
    try:
        found = load_pack(country)
    except PackError as exc:
        raise _unknown(country) from exc
    return NationalPackOut(
        country=found.country,
        country_name=found.country_name,
        authority=found.authority,
        authority_url=found.authority_url,
        summary=found.summary,
        complete=found.complete,
        items=[_item(i) for i in found.items],
        unverified_ids=list(found.unverified_ids),
        warning=found.warning(),
    )


@router.get(
    "/operations/{operation_id}/checklist",
    response_model=SubmissionChecklistOut,
    summary="The submission checklist for one operation, at its current SAIL",
)
def checklist(
    operation_id: UUID,
    ctx: OrgContextDep,
    repo: RepoDep,
) -> SubmissionChecklistOut:
    operation = own_operation(repo, ctx, operation_id)
    org = repo.get_org(ctx.org_id)
    country = str(org.get("country") or "EU").upper()

    determination = repo.latest_determination(operation["id"])
    sail = determination.get("sail") if determination else None
    required = frozenset(
        str(o.get("oso_id"))
        for o in (determination or {}).get("osos", [])
        if isinstance(o, dict) and o.get("is_required")
    )

    try:
        due, pending = tailor(country, sail=sail, required_osos=required)
        found = load_pack(country)
    except PackError as exc:
        raise _unknown(country) from exc

    return SubmissionChecklistOut(
        operation_id=UUID(str(operation["id"])),
        country=found.country,
        country_name=found.country_name,
        authority=found.authority,
        authority_url=found.authority_url,
        summary=found.summary,
        sail=sail,
        due=[_item(i) for i in due],
        pending=[_item(i) for i in pending],
        evidence_attached=len(repo.list_evidence(operation["id"])),
        dossier_versions=len(repo.list_dossiers(operation["id"])),
        warning=found.warning(),
        disclaimer=DISCLAIMER,
    )
