"""What the engine is reasoning with, and how much of it has been verified.

This endpoint exists so the UNVERIFIED state is a fact the client can read rather than a
string buried in a warning. A compliance officer should be able to ask the product what
it has actually checked.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.schemas import RulebaseOut, RulebaseTableOut
from app.engine.rulebase.loader import load_rulebase, rulebase_version

router = APIRouter(tags=["rulebase"])

#: What each unverified table still needs. Shown to the operator, not just logged.
SOURCES: dict[str, str] = {
    "igrc": "JARUS SORA 2.5 main body — intrinsic ground risk class table",
    "igrc_columns": "JARUS SORA 2.5 main body — iGRC column limits",
    "thresholds": "JARUS SORA 2.5 main body and Annex C — scope thresholds",
    "m1_m2": "JARUS SORA 2.5 Annex B — ground risk mitigations",
    "arc": "JARUS SORA 2.5 Annex C — initial air risk class",
    "arc_residual": "JARUS SORA 2.5 Annex C — strategic air risk mitigation",
    "sail": "JARUS SORA 2.5 main body — SAIL matrix",
    "oso": "JARUS SORA 2.5 main body — OSO assignment matrix",
    "containment": "JARUS SORA 2.5 main body — containment requirements",
    "tmpr": "JARUS SORA 2.5 Annex D — tactical mitigation performance",
    "buffers": "JARUS SORA 2.5 / Annex B — operational volume method",
    "citations": "The documents above, for page references",
    "cf_costs": "Owner review — these are our effort weights, not a regulation",
    "density_environment_hint": "Owner review — our prefill thresholds, not a regulation",
}


@router.get("/rulebase/current", response_model=RulebaseOut)
def current() -> RulebaseOut:
    tables = load_rulebase()
    unverified = sorted(name for name, t in tables.items() if not t.verified)
    return RulebaseOut(
        version=rulebase_version(),
        is_current=True,
        tables=[
            RulebaseTableOut(
                name=name,
                document=t.document,
                section=t.section,
                page=t.page,
                rows=len(t.rows),
                verified=t.verified,
            )
            for name, t in sorted(tables.items())
        ],
        unverified_tables=unverified,
        verified=not unverified,
        changelog=(
            "Seed skeleton. No table has been verified against an official source, so "
            "every determination carries an UNVERIFIED warning and must not be submitted "
            "to an authority."
            if unverified
            else "All tables verified."
        ),
        sources_needed=sorted({SOURCES.get(name, name) for name in unverified}),
    )
