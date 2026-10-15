"""The ONLY module in this codebase permitted to import ``anthropic``.

Three bounded jobs, none of which is a determination:

1. **Conversational intake** — operator prose becomes ``Candidate`` facts via tool-use
   against a strict schema. Temperature 0. The schema has no conclusion field, so there
   is nothing for the model to conclude into, and any field outside
   ``PROPOSABLE_FIELDS`` is dropped before it is returned.
2. **Dossier prose** — ConOps narrative, ERP skeleton, OSO compliance narrative. Input is
   a computed determination plus the operator's own inputs. The system prompt forbids
   restating, contradicting or recomputing any risk value, and the caller re-checks the
   output for invented risk vocabulary before it reaches a document.
3. **Trace explanation** — plain language for one trace node, grounded in the citation
   that node already carries.

What this module must never do, enforced by ``tests/test_boundary.py``:

* import ``app.engine``, ``app.db`` or ``app.services.determination`` — **transitively**,
  not merely directly, which is why it reads field metadata from ``app.domain.fields``
* write to the ``determinations`` table

Every call is logged by the caller with the prompt hash, model, token counts and latency,
and the monthly per-org cap is checked **before** the call. This module takes the usage
count as an argument because it may not reach the database to look it up itself.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from app.domain.fields import FIELD_LABELS, PROPOSABLE_FIELDS

log = logging.getLogger(__name__)

Purpose = str  # "intake" | "dossier_prose" | "trace_explanation"

#: Temperature 0 everywhere. Extraction and description are not creative tasks, and a
#: compliance tool that gives a different answer to the same prose is not usable.
TEMPERATURE = 0.0

MAX_TOKENS_INTAKE = 1500
MAX_TOKENS_PROSE = 2000

INTAKE_SYSTEM = """\
You extract candidate facts from a drone operator's description of a flight, for a
European SORA compliance tool.

You do not assess risk. You never state or imply a ground risk class, an air risk class,
a SAIL, an OSO, a robustness requirement, or whether a flight is permitted. A separate
symbolic rules engine computes all of that. Your only job is to turn prose into
candidate values for named fields, which the operator then confirms or corrects.

Rules:
- Only emit a fact you can point at in the operator's own words. Quote that span.
- Emit nothing you inferred from aviation knowledge rather than from the text. If the
  operator did not say the altitude, do not supply a typical one.
- One fact per field. If the text is ambiguous about a field, omit it.
- Confidence is about the TEXT, not about the flight: 0.9 when the operator stated the
  value plainly, 0.6 when you are reading it from context, below 0.6 when it is a guess.
- For `drone_id`, use only an id from the fleet you are given. Never invent an aircraft.
- Never emit a field that is not in the tool schema.

If the text contains nothing extractable, call the tool with an empty list."""

PROSE_SYSTEM = """\
You write the narrative sections of a SORA dossier for a European drone operator.

Every risk value in this dossier was computed by a symbolic rules engine and is supplied
to you below. You must not restate, recompute, contradict, round, re-explain or
second-guess any of them. You may refer to a value only in the exact form given.

You must not introduce any risk classification the engine did not supply: no iGRC, GRC,
ARC, SAIL, OSO level, robustness level, TMPR or containment level beyond what is in the
supplied data.

Every factual sentence you write must correspond to a supplied fact. Where the data does
not support a statement an authority would expect, write that the information is not yet
established rather than filling the gap.

Write in the register of a pre-flight checklist: precise, calm, declarative. Sentence
case, active voice, no filler, no exclamation marks. Do not use the words effortless,
seamless, magic, revolutionise, unlock, empower, game-changing or supercharge."""

#: Risk vocabulary the prose job is not allowed to originate. Checked on the way out,
#: because a system prompt is an instruction and not a guarantee.
FORBIDDEN_IN_PROSE = (
    "igrc",
    "grc ",
    "sail ",
    "arc ",
    "tmpr",
    "robustness",
    "containment",
)


class LlmError(RuntimeError):
    """The language model could not be used. Never raised in place of a determination."""


class CapReached(LlmError):
    """The organisation's monthly allowance is spent."""


@dataclass(frozen=True, slots=True)
class LlmCall:
    """What a call cost, for the ``llm_calls`` audit row the caller writes."""

    purpose: Purpose
    model: str
    prompt_hash: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


@dataclass(frozen=True, slots=True)
class Extraction:
    """Candidate facts plus the prose reply, and what it cost."""

    facts: list[dict[str, Any]]
    reply: str
    call: LlmCall


def assert_within_cap(*, monthly_cap: int, used_this_month: int) -> None:
    """Raise before any call that would exceed the organisation's allowance.

    The count is passed in: this module may not reach the database, so the API layer
    reads it and supplies it.
    """
    if monthly_cap and used_this_month >= monthly_cap:
        raise CapReached(
            f"This organisation has used its {monthly_cap} language-model calls for the "
            "month. Determinations are unaffected: they are computed by the rules engine, "
            "not by a language model. You can still enter facts in the wizard directly."
        )


def prompt_hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ the tool schema


def intake_tool() -> dict[str, Any]:
    """The extraction tool. No conclusion field exists for the model to use."""
    return {
        "name": "propose_facts",
        "description": (
            "Record candidate facts extracted from the operator's text. Each fact is a "
            "proposal the operator will confirm or reject; none of them is a conclusion."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {
                                "type": "string",
                                "enum": sorted(PROPOSABLE_FIELDS),
                                "description": "Which mission field this value belongs to.",
                            },
                            "value": {
                                "description": (
                                    "The value, in the field's own units: metres for "
                                    "altitude, people per km² for density, the enum "
                                    "value for a choice, a fleet id for the aircraft, "
                                    "and low/medium/high for a mitigation."
                                )
                            },
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "source_span": {
                                "type": "string",
                                "description": "The operator's own words this came from.",
                            },
                        },
                        "required": ["field", "value", "confidence", "source_span"],
                    },
                },
                "note": {
                    "type": "string",
                    "description": "One sentence on what was extracted. Never a conclusion.",
                },
            },
            "required": ["facts"],
        },
    }


def _client(api_key: str) -> Any:
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - the dependency is pinned
        raise LlmError("the anthropic SDK is not installed") from exc
    return anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=30.0)


def _field_guide(fleet: list[dict[str, Any]]) -> str:
    lines = ["Fields you may propose, and what each means:"]
    for field in sorted(PROPOSABLE_FIELDS):
        lines.append(f"  {field} — {FIELD_LABELS.get(field, field)}")
    if fleet:
        lines.append("\nThe operator's fleet. Use these ids for drone_id and no others:")
        for drone in fleet:
            lines.append(
                f"  id={drone.get('id')}  {drone.get('name')}"
                f"{f' ({drone.get('registration')})' if drone.get('registration') else ''}"
                f" — {drone.get('max_dimension_m')} m, {drone.get('mtom_kg')} kg"
            )
    else:
        lines.append("\nThe operator has no aircraft on file, so do not propose drone_id.")
    return "\n".join(lines)


def extract_facts(
    text: str,
    *,
    fleet: list[dict[str, Any]],
    api_key: str,
    model: str,
    monthly_cap: int,
    used_this_month: int,
) -> Extraction:
    """Prose → candidate facts, via tool-use. Raises rather than guessing on failure."""
    assert_within_cap(monthly_cap=monthly_cap, used_this_month=used_this_month)

    guide = _field_guide(fleet)
    started = time.perf_counter()
    try:
        response = _client(api_key).messages.create(
            model=model,
            max_tokens=MAX_TOKENS_INTAKE,
            temperature=TEMPERATURE,
            system=INTAKE_SYSTEM,
            tools=[intake_tool()],
            tool_choice={"type": "tool", "name": "propose_facts"},
            messages=[{"role": "user", "content": f"{guide}\n\nThe operator wrote:\n\n{text}"}],
        )
    except Exception as exc:  # the SDK raises a family of errors; all are the same to us
        raise LlmError(f"the intake model did not answer: {exc}") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    payload: dict[str, Any] = {}
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            payload = dict(getattr(block, "input", {}) or {})
            break

    facts = _clean(payload.get("facts") or [], fleet)
    note = str(payload.get("note") or "").strip()

    return Extraction(
        facts=facts,
        reply=note or _fallback_note(facts),
        call=LlmCall(
            purpose="intake",
            model=model,
            prompt_hash=prompt_hash(INTAKE_SYSTEM, guide, text),
            input_tokens=int(getattr(response.usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(response.usage, "output_tokens", 0) or 0),
            latency_ms=latency_ms,
        ),
    )


def _clean(raw: list[Any], fleet: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop anything the model should not have produced.

    The schema constrains the model; this constrains the output. A model that returns an
    unknown field, an out-of-range confidence, or an aircraft the operator does not own
    gets that proposal discarded rather than shown.
    """
    fleet_ids = {str(d.get("id")) for d in fleet}
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field", ""))
        if field not in PROPOSABLE_FIELDS or field in seen:
            continue
        try:
            confidence = float(item.get("confidence", 0))
        except (TypeError, ValueError):
            continue
        if not 0 <= confidence <= 1:
            continue
        if field == "drone_id" and str(item.get("value")) not in fleet_ids:
            log.warning("intake model proposed an aircraft outside the fleet; dropped")
            continue
        span = str(item.get("source_span") or "").strip()
        if not span:
            # No span means no evidence in the operator's words, which is the one thing
            # extraction is not allowed to do.
            continue
        seen.add(field)
        out.append(
            {
                "field": field,
                "value": item.get("value"),
                "confidence": confidence,
                "source_span": span[:400],
            }
        )
    return out


def _fallback_note(facts: list[dict[str, Any]]) -> str:
    if not facts:
        return "Nothing in that reached a fact the wizard holds."
    names = [FIELD_LABELS.get(str(f["field"]), str(f["field"])) for f in facts]
    listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" and {names[-1]}"
    return (
        f"Picked out {listed}. Nothing here has reached the engine — confirm each one, or "
        "correct it, and the determination runs on what you confirmed."
    )


# ------------------------------------------------------------------ dossier prose


@dataclass(frozen=True, slots=True)
class Prose:
    sections: dict[str, str]
    call: LlmCall


def write_prose(
    *,
    brief: dict[str, Any],
    sections: list[str],
    api_key: str,
    model: str,
    monthly_cap: int,
    used_this_month: int,
) -> Prose:
    """Narrative sections from a determination that is already final.

    ``brief`` is supplied by the caller and contains the computed values verbatim. This
    function does not read a determination from anywhere: it cannot, by construction.
    """
    assert_within_cap(monthly_cap=monthly_cap, used_this_month=used_this_month)

    tool = {
        "name": "write_sections",
        "description": "Write the requested narrative sections.",
        "input_schema": {
            "type": "object",
            "properties": {
                s: {"type": "string", "description": f"The {s.replace('_', ' ')} section."}
                for s in sections
            },
            "required": sections,
        },
    }
    body = json.dumps(brief, indent=2, sort_keys=True, default=str)
    started = time.perf_counter()
    try:
        response = _client(api_key).messages.create(
            model=model,
            max_tokens=MAX_TOKENS_PROSE,
            temperature=TEMPERATURE,
            system=PROSE_SYSTEM,
            tools=[tool],
            tool_choice={"type": "tool", "name": "write_sections"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write the sections from this data only. Every risk value below "
                        "was computed by the rules engine and is final.\n\n" + body
                    ),
                }
            ],
        )
    except Exception as exc:
        raise LlmError(f"the prose model did not answer: {exc}") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    payload: dict[str, Any] = {}
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            payload = dict(getattr(block, "input", {}) or {})
            break

    written = {k: str(v) for k, v in payload.items() if k in sections and isinstance(v, str)}
    return Prose(
        sections=written,
        call=LlmCall(
            purpose="dossier_prose",
            model=model,
            prompt_hash=prompt_hash(PROSE_SYSTEM, body),
            input_tokens=int(getattr(response.usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(response.usage, "output_tokens", 0) or 0),
            latency_ms=latency_ms,
        ),
    )


def originates_risk_vocabulary(text: str, allowed: set[str]) -> list[str]:
    """Risk terms in generated prose that the supplied data does not contain.

    The system prompt forbids inventing a risk value; this is the check that it did not.
    Used by the dossier builder to refuse a section rather than print it.
    """
    lowered = text.lower()
    allowed_lower = {a.lower() for a in allowed}
    found: list[str] = []
    for term in FORBIDDEN_IN_PROSE:
        if term in lowered and not any(term in a for a in allowed_lower):
            found.append(term.strip())
    return found
