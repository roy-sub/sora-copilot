"""Facts in, Determination out.

Loads the rulebase, grounds the mission facts, solves with ``--models=1``, and hands the
single answer set to the trace formatter. More than one answer set is a rulebase bug, not
an ambiguity to resolve at runtime (build spec §6.4), and the solver call asserts on it.

Not implemented until Phase 2. It raises rather than returning a plausible value: a
determination that nobody computed is the one thing this product must never produce.
"""

from __future__ import annotations

from app.domain import Determination, Mission


def determine(mission: Mission, *, rulebase_version: str) -> Determination:
    raise NotImplementedError("Phase 2: the clingo rulebase is not written yet.")
