"""OSO evidence, and the dossier.

Generation is **synchronous**. The build spec shapes it as a job id, and the response
keeps that shape, but a Render free instance can be put to sleep mid-job and a queued
``BackgroundTasks`` job would vanish without telling anyone. A single-operation DOCX
renders in a second or two, so it is produced inline and the signed URL comes back with
it. PLAN.md §4.3 records the decision.

A generated dossier is stored whole rather than regenerated on demand: regenerating it
against a newer rulebase would silently produce a different document under the same
version number.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response

from app.api.v1.deps_api import RepoDep, not_found
from app.api.v1.schemas import (
    DossierIn,
    DossierOut,
    DossierSectionOut,
    DossierStatusOut,
    EvidenceOut,
    OsoOut,
)
from app.config import Settings, get_settings
from app.db.repo import NotFound, Row
from app.deps import CurrentUserDep, OrgContextDep
from app.problem import ProblemError
from app.services import determination as determination_service
from app.services import dossier as builder
from app.services import intake, llm, storage

log = logging.getLogger(__name__)

router = APIRouter(prefix="/operations", tags=["dossier"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


def _own(repo: RepoDep, org_id: UUID, operation_id: UUID) -> Row:
    try:
        return repo.get_operation(org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc


# ------------------------------------------------------------------ OSOs and evidence


@router.get("/{operation_id}/osos", response_model=list[OsoOut], tags=["determination"])
def list_osos(operation_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> list[OsoOut]:
    """The OSO set from the stored determination, with whatever evidence is attached."""
    _own(repo, ctx.org_id, operation_id)
    determination = repo.latest_determination(operation_id)
    if determination is None:
        raise ProblemError(
            code="no_determination",
            title="This operation has not been run yet",
            status_code=404,
            detail="The OSO set is assigned from the computed SAIL, so run the determination first.",
        )
    evidence = repo.list_evidence(operation_id)
    by_oso: dict[str, list[Row]] = {}
    for item in evidence:
        by_oso.setdefault(str(item.get("oso_id") or ""), []).append(item)

    out: list[OsoOut] = []
    for oso in determination["osos"]:
        files = by_oso.get(str(oso["oso_id"]), [])
        status_value = oso.get("status", "unmet")
        if files and status_value == "unmet":
            # Evidence attached but not yet reviewed: documented, not verified. Calling
            # it verified would be the tool vouching for a document nobody checked.
            status_value = "documented"
        out.append(
            OsoOut(
                oso_id=oso["oso_id"],
                title=oso["title"],
                required_robustness=oso["required_robustness"],
                citation=oso["citation"],
                status=status_value,
                evidence=[_evidence_out(f) for f in files],
                what_it_requires=oso["title"],
                checklist=[],
            )
        )
    return out


def _evidence_out(row: Row) -> EvidenceOut:
    return EvidenceOut(
        id=row["id"],
        oso_id=row.get("oso_id"),
        filename=row["filename"],
        bytes=row.get("bytes"),
        content_type=row.get("content_type"),
        storage_path=row["storage_path"],
        uploaded_at=row["uploaded_at"],
    )


@router.get("/{operation_id}/evidence", response_model=list[EvidenceOut], tags=["determination"])
def list_evidence(operation_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> list[EvidenceOut]:
    _own(repo, ctx.org_id, operation_id)
    return [_evidence_out(r) for r in repo.list_evidence(operation_id)]


@router.post(
    "/{operation_id}/evidence",
    response_model=EvidenceOut,
    status_code=status.HTTP_201_CREATED,
    tags=["determination"],
)
async def upload_evidence(
    operation_id: UUID,
    ctx: OrgContextDep,
    user: CurrentUserDep,
    repo: RepoDep,
    file: Annotated[UploadFile, File()],
    oso_id: Annotated[str | None, Form()] = None,
) -> EvidenceOut:
    """Attach a file to an OSO, or to the operation as a whole.

    The file is validated before it is stored — size and type — so the operator learns
    immediately rather than when someone tries to read it.
    """
    _own(repo, ctx.org_id, operation_id)
    data = await file.read()
    filename = file.filename or "evidence"
    try:
        content_type = storage.validate_evidence(filename, len(data), file.content_type)
    except storage.RejectedFile as exc:
        raise ProblemError(
            code="file_rejected",
            title="That file was not accepted",
            status_code=422,
            detail=exc.reason,
        ) from exc

    store = storage.get_storage()
    path = storage.evidence_path(str(operation_id), oso_id, filename)
    try:
        stored = store.put(storage.EVIDENCE_BUCKET, path, data, content_type)
    except storage.StorageError as exc:
        raise ProblemError(
            code="storage_failed",
            title="The file could not be stored",
            status_code=503,
            detail=str(exc),
        ) from exc

    row = repo.add_evidence(
        operation_id,
        {
            "oso_id": oso_id,
            "mitigation_id": None,
            "storage_path": stored.path,
            "filename": filename,
            "bytes": stored.bytes,
            "content_type": stored.content_type,
            "uploaded_by": str(user.id),
        },
    )
    return _evidence_out(row)


@router.delete(
    "/{operation_id}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["determination"],
)
def delete_evidence(
    operation_id: UUID, evidence_id: UUID, ctx: OrgContextDep, repo: RepoDep
) -> None:
    _own(repo, ctx.org_id, operation_id)
    try:
        row = next(r for r in repo.list_evidence(operation_id) if str(r["id"]) == str(evidence_id))
    except StopIteration as exc:
        raise not_found("evidence file") from exc
    try:
        storage.get_storage().delete(storage.EVIDENCE_BUCKET, str(row["storage_path"]))
    except storage.StorageError as exc:
        # The record is what the dossier reads, so remove it even if the object is gone.
        log.warning("could not delete the stored object: %s", exc)
    repo.delete_evidence(operation_id, evidence_id)


@router.get("/{operation_id}/evidence/{evidence_id}/download", tags=["determination"])
def download_evidence(
    operation_id: UUID, evidence_id: UUID, ctx: OrgContextDep, repo: RepoDep
) -> Response:
    _own(repo, ctx.org_id, operation_id)
    try:
        row = next(r for r in repo.list_evidence(operation_id) if str(r["id"]) == str(evidence_id))
    except StopIteration as exc:
        raise not_found("evidence file") from exc
    store = storage.get_storage()
    if (url := _signed(store, storage.EVIDENCE_BUCKET, str(row["storage_path"]))) is not None:
        return Response(status_code=307, headers={"location": url})
    try:
        data = store.get(storage.EVIDENCE_BUCKET, str(row["storage_path"]))
    except storage.StorageError as exc:
        raise ProblemError(
            code="file_unavailable",
            title="That file is no longer stored",
            status_code=410,
            detail=str(exc),
        ) from exc
    return Response(
        content=data,
        media_type=str(row.get("content_type") or "application/octet-stream"),
        headers={"content-disposition": f'attachment; filename="{row["filename"]}"'},
    )


def _signed(store: storage.Storage, bucket: str, path: str) -> str | None:
    try:
        return store.signed_url(bucket, path)
    except storage.StorageError:
        return None


# ------------------------------------------------------------------ the dossier


SECTION_NAMES: list[tuple[str, str]] = [
    ("conops", "ConOps"),
    ("tables", "SORA assessment tables"),
    ("osos", "OSO matrix"),
    ("evidence", "Mitigation evidence index"),
    ("erp", "ERP skeleton"),
    ("trace", "Derivation trace appendix"),
]


@router.get("/{operation_id}/dossier", response_model=DossierStatusOut)
def dossier_status(operation_id: UUID, ctx: OrgContextDep, repo: RepoDep) -> DossierStatusOut:
    """What each section contains, and whether a dossier can be generated at all."""
    _own(repo, ctx.org_id, operation_id)
    determination = repo.latest_determination(operation_id)
    evidence = repo.list_evidence(operation_id)
    versions = repo.list_dossiers(operation_id)

    sections: list[DossierSectionOut] = []
    if determination is None:
        for key, name in SECTION_NAMES:
            sections.append(
                DossierSectionOut(key=key, name=name, state="not_started", meta="no determination")
            )
        return DossierStatusOut(
            operation_id=operation_id,
            sections=sections,
            versions=[_dossier_out(v, None) for v in versions],
            next_version=repo.next_dossier_version(operation_id),
            can_generate=False,
            blocker="Run the determination first. Every table in the dossier is a rendering of it.",
        )

    osos = determination["osos"]
    required = [o for o in osos if o.get("required_robustness") != "none"]
    evidenced = {str(e.get("oso_id")) for e in evidence if e.get("oso_id")}
    gaps = [o for o in required if str(o["oso_id"]) not in evidenced]
    trace_count = len(determination.get("trace") or [])

    state_for: dict[str, tuple[str, str]] = {
        "conops": ("complete", "from the confirmed facts"),
        "tables": ("complete", "6 tables"),
        "osos": (
            "complete" if not gaps else "partial",
            f"{len(required)} required" if not gaps else f"{len(gaps)} without evidence",
        ),
        "evidence": (
            "complete" if evidence else "not_started",
            f"{len(evidence)} file{'s' if len(evidence) != 1 else ''}" if evidence else "none attached",
        ),
        "erp": ("not_started", "skeleton only — yours to complete"),
        "trace": ("complete", f"{trace_count} nodes"),
    }
    for key, name in SECTION_NAMES:
        state, meta = state_for[key]
        sections.append(DossierSectionOut(key=key, name=name, state=state, meta=meta))

    return DossierStatusOut(
        operation_id=operation_id,
        sections=sections,
        versions=[_dossier_out(v, None) for v in versions],
        next_version=repo.next_dossier_version(operation_id),
        can_generate=True,
        blocker=None,
    )


def _dossier_out(row: Row, url: str | None) -> DossierOut:
    return DossierOut(
        id=row["id"],
        operation_id=row["operation_id"],
        determination_id=row.get("determination_id"),
        version=int(row["version"]),
        format=row.get("format", "docx"),
        storage_path=row["storage_path"],
        note=row.get("note"),
        generated_at=row["generated_at"],
        download_url=url,
    )


@router.post("/{operation_id}/dossier", response_model=DossierOut, status_code=status.HTTP_201_CREATED)
def generate(
    operation_id: UUID,
    body: DossierIn,
    ctx: OrgContextDep,
    repo: RepoDep,
    settings: SettingsDep,
) -> DossierOut:
    operation = _own(repo, ctx.org_id, operation_id)
    determination = repo.latest_determination(operation_id)
    if determination is None:
        raise ProblemError(
            code="no_determination",
            title="Run the determination first",
            status_code=409,
            detail="Every table in the dossier is a rendering of a stored determination.",
        )

    facts = repo.list_facts(operation_id)
    mission = intake.apply_confirmed(dict(operation.get("mission") or {}), facts)
    drone_id = mission.get("drone_id")
    drone = None
    if drone_id:
        try:
            drone = repo.get_drone(ctx.org_id, UUID(str(drone_id)))
        except (NotFound, ValueError):
            drone = None

    prose = _prose(repo, ctx.org_id, determination, mission, settings)
    version = repo.next_dossier_version(operation_id)
    geo = _geo_summary(repo, ctx.org_id, operation_id)

    data = builder.DossierInput(
        operation=operation,
        organisation=repo.get_org(ctx.org_id),
        drone=drone,
        mission=mission,
        determination=determination,
        evidence=repo.list_evidence(operation_id),
        geo=geo,
        version=version,
        prose=prose,
        outlines=geo,
    )
    document = builder.build(data)

    store = storage.get_storage()
    path = storage.dossier_path(str(operation_id), version, body.format)
    try:
        stored = store.put(storage.DOSSIER_BUCKET, path, document, storage.DOCX_TYPE)
    except storage.StorageError as exc:
        raise ProblemError(
            code="storage_failed",
            title="The dossier could not be stored",
            status_code=503,
            detail=str(exc),
        ) from exc

    row = repo.add_dossier(
        operation_id,
        {
            "determination_id": determination["id"],
            "version": version,
            "storage_path": stored.path,
            "format": body.format,
            "note": body.note,
        },
    )
    if operation.get("status") in ("draft", "determined"):
        repo.update_operation(ctx.org_id, operation_id, {"status": "dossier_ready"})
    return _dossier_out(row, _signed(store, storage.DOSSIER_BUCKET, stored.path))


def _geo_summary(repo: RepoDep, org_id: UUID, operation_id: UUID) -> dict[str, object] | None:
    """Re-derive the volume figures for the document, from the saved geometry."""
    try:
        return determination_service.derive_geo(repo, org_id, operation_id)
    except Exception as exc:  # a dossier without areas is better than no dossier
        log.info("dossier: volumes not available (%s)", exc)
        return None


def _prose(
    repo: RepoDep,
    org_id: UUID,
    determination: Row,
    mission: dict[str, object],
    settings: Settings,
) -> dict[str, str] | None:
    """LLM narrative, if a key is configured and the output survives the check.

    The generated text is scanned for risk vocabulary the supplied data does not contain.
    If the model originated a risk term, the section is **discarded** and the document
    falls back to prose written from the facts — a sentence a model invented about a risk
    class is exactly what this product exists not to produce.
    """
    if not settings.anthropic_configured:
        return None

    computed: dict[str, object] = {
        "igrc": determination.get("igrc"),
        "final_grc": determination.get("final_grc"),
        "initial_arc": determination.get("initial_arc"),
        "residual_arc": determination.get("residual_arc"),
        "sail": determination.get("sail"),
        "tmpr": determination.get("tmpr"),
        "containment": determination.get("containment"),
    }
    brief: dict[str, object] = {
        "operation": {
            k: mission.get(k) for k in ("operation_type", "ground_environment", "airspace_class")
        },
        "volume": mission.get("volume"),
        "population_density_per_km2": mission.get("population_density_per_km2"),
        "mitigations": mission.get("mitigations"),
        "computed": computed,
    }
    # The vocabulary the model is permitted to use, drawn from what it was given.
    allowed = {str(v).lower() for v in computed.values() if v is not None}
    allowed.add(f"sail {computed['sail']}".lower())

    try:
        result = llm.write_prose(
            brief=brief,
            sections=["conops", "erp"],
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            monthly_cap=settings.llm_monthly_call_cap,
            used_this_month=repo.count_llm_calls_this_month(org_id),
        )
    except llm.LlmError as exc:
        log.warning("dossier prose unavailable, writing from the facts instead: %s", exc)
        return None

    repo.log_llm_call(
        org_id,
        {
            "purpose": result.call.purpose,
            "model": result.call.model,
            "prompt_hash": result.call.prompt_hash,
            "input_tokens": result.call.input_tokens,
            "output_tokens": result.call.output_tokens,
            "latency_ms": result.call.latency_ms,
        },
    )

    kept: dict[str, str] = {}
    for key, text in result.sections.items():
        invented = llm.originates_risk_vocabulary(text, allowed)
        if invented:
            log.warning("discarded the %s section: it originated %s", key, invented)
            continue
        kept[key] = text
    return kept or None


@router.get("/{operation_id}/dossier/{dossier_id}/download")
def download(
    operation_id: UUID, dossier_id: UUID, ctx: OrgContextDep, repo: RepoDep
) -> Response:
    _own(repo, ctx.org_id, operation_id)
    try:
        row = next(d for d in repo.list_dossiers(operation_id) if str(d["id"]) == str(dossier_id))
    except StopIteration as exc:
        raise not_found("dossier") from exc

    store = storage.get_storage()
    if (url := _signed(store, storage.DOSSIER_BUCKET, str(row["storage_path"]))) is not None:
        return Response(status_code=307, headers={"location": url})
    try:
        data = store.get(storage.DOSSIER_BUCKET, str(row["storage_path"]))
    except storage.StorageError as exc:
        raise ProblemError(
            code="file_unavailable",
            title="That dossier is no longer stored",
            status_code=410,
            detail=f"{exc} Generate a new version — the determination it renders is unchanged.",
        ) from exc
    name = f"sora-dossier-v{row['version']}.{row.get('format', 'docx')}"
    return Response(
        content=data,
        media_type=storage.DOCX_TYPE,
        headers={"content-disposition": f'attachment; filename="{name}"'},
    )
