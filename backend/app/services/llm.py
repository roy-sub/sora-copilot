"""The ONLY module in this codebase permitted to import ``anthropic``.

Three bounded jobs, none of which is a determination:

1. **Conversational intake** — operator prose becomes ``ProposedFact`` objects via
   tool-use against a strict schema mirroring ``Mission``. Temperature 0. The schema has
   no conclusion field, so there is nothing for the model to conclude into.
2. **Dossier prose** — ConOps narrative, ERP skeleton, OSO compliance narrative. Input is
   a computed ``Determination`` plus the operator's own inputs. The system prompt forbids
   restating, contradicting or recomputing any risk value.
3. **Trace explanation** — plain language for one ``TraceNode``, grounded in a retrieved
   quote from the official text.

What this module must never do, enforced by ``tests/test_boundary.py``:

* import ``app.engine.runner`` or anything else that computes a determination
* import anything under ``app.db``
* write to the ``determinations`` table

Every call is logged to ``llm_calls`` with the prompt hash, model, token counts and
latency, and the monthly per-org cap is checked *before* the call, not after.

Not implemented until Phase 6. The cap check is signature-only here so the boundary test
has a real module to assert against from the first commit.
"""

from __future__ import annotations

from uuid import UUID

Purpose = str  # "intake" | "dossier_prose" | "trace_explanation"


def assert_within_cap(org_id: UUID, *, purpose: Purpose, monthly_cap: int, used_this_month: int) -> None:
    """Raise before any call that would exceed the org's monthly allowance.

    The caller supplies ``used_this_month`` because this module may not reach the
    database itself — the count is read by the API layer and passed in.
    """
    if monthly_cap and used_this_month >= monthly_cap:
        raise RuntimeError(
            f"Monthly language-model call cap of {monthly_cap} reached for this organisation. "
            "Determinations are unaffected: they are computed by the rules engine."
        )
