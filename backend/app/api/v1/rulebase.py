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

#: What each still-unverified table needs, named by the document that closes it. Shown
#: to the operator, not just logged: "something is unverified" is not a work item, and
#: "Figure 4 of the Main Body release" is.
SOURCES: dict[str, str] = {
    "thresholds": "JARUS SORA 2.5 Main Body (JAR_doc_25) — Figure 4, for the 500 ft band",
    "m1_m2": "JARUS SORA 2.5 Main Body (JAR_doc_25) Table 5, and Annex B",
    "arc": "JARUS SORA 2.5 Main Body (JAR_doc_25) — Figure 4, all 13 branches",
    "arc_residual": "JARUS SORA 2.5 Annex C — Step #5 residual ARC",
    "oso": "JARUS SORA 2.5 Main Body (JAR_doc_25) Step #9, and Annex E (JAR_doc_28)",
    "containment": "JARUS SORA 2.5 Main Body (JAR_doc_25) Step #7 — tier names and levels",
    "tmpr": "JARUS SORA 2.5 Annex D — TMPR by residual ARC",
    "buffers": "JARUS SORA 2.5 Annex A (JAR_doc_26) — contingency volume and adjacent area",
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
                basis=t.basis,
                needs=t.needs,
                adopted_by=t.adopted_by,
            )
            for name, t in sorted(tables.items())
        ],
        unverified_tables=unverified,
        verified=not unverified,
        changelog=(
            f"{len(tables) - len(unverified)} of {len(tables)} tables verified. "
            f"{len(unverified)} still carry seed values, so a determination that reads "
            f"one of them carries an UNVERIFIED warning naming it and must not be "
            f"submitted to an authority. Each table's own header says what it needs."
            if unverified
            else "All tables verified."
        ),
        sources_needed=sorted({SOURCES.get(name, name) for name in unverified}),
    )
