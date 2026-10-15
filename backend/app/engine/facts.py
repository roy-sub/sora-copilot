"""Mission → ASP ground atoms.

One function per fact family, each emitting ``fact/2`` atoms with the operator's own
vocabulary. Nothing here interprets; the interpretation lives in the .lp rules.

Not implemented until Phase 2.
"""

from __future__ import annotations

from app.domain import Mission


def render(mission: Mission) -> str:
    raise NotImplementedError("Phase 2: fact rendering is not written yet.")
