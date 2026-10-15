"""What minimal change reaches SAIL ≤ target.

Phase 5 ships bounded enumeration: for each single-parameter change in a discrete
candidate list, re-run the engine and keep the changes that lower SAIL, ranked by an
effort cost from ``tables/cf_costs.csv``. Phase 7 adds Z3 optimisation for genuine
minimal multi-parameter change sets, with the enumeration retained as the fallback and a
cross-check test that both agree on single-parameter cases.

Not implemented until Phase 5.
"""

from __future__ import annotations

from app.domain import CounterfactualSuggestion, Mission


def suggest(
    mission: Mission, *, target_sail: str | None = None, rulebase_version: str
) -> list[CounterfactualSuggestion]:
    raise NotImplementedError("Phase 5: the counterfactual search is not written yet.")
