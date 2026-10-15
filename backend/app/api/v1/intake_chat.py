"""Conversational intake: prose in, candidate facts out.

The visible boundary between the language model and the engine. The response is a list
of **proposals**, each with the operator's own words it came from, every one pending until
the operator confirms it. Nothing here can produce a risk value.

Two extractors behind one response shape:

* ``llm`` when ``ANTHROPIC_API_KEY`` is set — tool-use against a strict schema, temperature 0.
* ``deterministic`` otherwise — regex and keywords, in ``services/extract.py``.

The response says which ran, because an operator should know whether a model read their
text. Swapping between them changes which facts are proposed and never what the engine
does with them.
"""

from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter

from app.api.v1.deps_api import RepoDep, SettingsDep, not_found
from app.api.v1.gate import GateDep
from app.api.v1.operations import _fact_out
from app.api.v1.schemas import IntakeChatIn, IntakeChatOut
from app.db.repo import NotFound
from app.deps import OrgContextDep
from app.problem import ProblemError
from app.services import extract as deterministic
from app.services import intake, llm

log = logging.getLogger(__name__)

router = APIRouter(prefix="/operations", tags=["intake"])



@router.post(
    "/{operation_id}/intake/chat",
    response_model=IntakeChatOut,
    summary="Turn prose into candidate facts — never into a conclusion",
)
def chat(
    operation_id: UUID,
    body: IntakeChatIn,
    ctx: OrgContextDep,
    repo: RepoDep,
    gate: GateDep,
    settings: SettingsDep,
) -> IntakeChatOut:
    try:
        repo.get_operation(ctx.org_id, operation_id)
    except NotFound as exc:
        raise not_found("operation") from exc

    # After the ownership check, so a 402 cannot confirm another operator's operation.
    # The prose panel is a paid feature; the wizard's form collects the same facts on
    # every plan, which is what the refusal says.
    gate.require_feature("conversational_intake")

    fleet = repo.list_drones(ctx.org_id)
    use_llm = settings.anthropic_configured

    if use_llm:
        used = repo.count_llm_calls_this_month(ctx.org_id)
        try:
            result = llm.extract_facts(
                body.text,
                fleet=fleet,
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
                monthly_cap=settings.llm_monthly_call_cap,
                used_this_month=used,
            )
        except llm.CapReached as exc:
            raise ProblemError(
                code="llm_cap_reached",
                title="This month's language-model allowance is spent",
                status_code=429,
                detail=str(exc),
            ) from exc
        except llm.LlmError as exc:
            # Fall back rather than fail: the deterministic extractor is always available,
            # and losing the panel because a third party is down would be worse than
            # extracting less from the same text.
            log.warning("intake model unavailable, using the deterministic extractor: %s", exc)
            use_llm = False
        else:
            repo.log_llm_call(
                ctx.org_id,
                {
                    "purpose": result.call.purpose,
                    "model": result.call.model,
                    "prompt_hash": result.call.prompt_hash,
                    "input_tokens": result.call.input_tokens,
                    "output_tokens": result.call.output_tokens,
                    "latency_ms": result.call.latency_ms,
                },
            )
            return _store(repo, operation_id, result.facts, result.reply, result.call.model, "llm")

    candidates = deterministic.extract(body.text, [dict(d) for d in fleet])
    facts = [
        {
            "field": c.field,
            "value": c.value,
            "confidence": c.confidence,
            "source_span": c.source_span,
        }
        for c in candidates
    ]
    return _store(
        repo,
        operation_id,
        facts,
        deterministic.summarise(candidates),
        "deterministic extractor",
        "deterministic",
    )


def _store(
    repo: RepoDep,
    operation_id: UUID,
    facts: list[dict[str, object]],
    reply: str,
    model: str,
    extractor: Literal["llm", "deterministic"],
) -> IntakeChatOut:
    """Persist the proposals as pending, and return them for confirmation."""
    try:
        validated = intake.validate_proposals(facts)
    except intake.IntakeError as exc:
        # The extractor proposed something outside the whitelist. That is a bug in the
        # extractor, not an operator error, so it fails loudly rather than being dropped.
        raise ProblemError(
            code="extraction_invalid",
            title="The extractor proposed a field that does not exist",
            status_code=500,
            detail=str(exc),
        ) from exc

    stored = repo.add_facts(operation_id, validated) if validated else []
    return IntakeChatOut(
        facts=[_fact_out(row) for row in stored],
        reply=reply,
        model=model,
        extractor=extractor,
    )
