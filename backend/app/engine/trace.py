"""clingo answer set → TraceNode tree.

Reads ``because/3`` atoms only. A conclusion with no matching justification cannot reach
this module, because the rulebase carries an integrity constraint that makes such a model
unsatisfiable.

Not implemented until Phase 2.
"""

from __future__ import annotations

from app.domain import Trace


def build(atoms: list[str]) -> Trace:
    raise NotImplementedError("Phase 2: the trace formatter is not written yet.")
