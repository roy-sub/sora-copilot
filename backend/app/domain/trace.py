"""The justification trace.

Every derived atom in the rulebase carries a ``because/3`` justification atom, and the
trace formatter reads only those. A conclusion with no matching ``because/3`` makes the
clingo model unsatisfiable (build spec §6.4) — so a determination without a complete
trace cannot be produced, rather than being produced and flagged.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.common import Citation, TraceNodeKind


class TraceNode(BaseModel):
    id: str
    conclusion: str = Field(description='Human-readable, e.g. "iGRC = 6"')
    rule_id: str = Field(description='Stable id, e.g. "sora25.igrc.row3.col4"')
    citation: Citation
    premises: list[str] = Field(
        default_factory=list, description="Ids of child nodes or of the facts this rests on."
    )
    kind: TraceNodeKind


class Trace(BaseModel):
    """A flat node list plus the root id; the tree is reconstructed from ``premises``."""

    nodes: list[TraceNode]
    root_id: str

    def by_id(self, node_id: str) -> TraceNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    @property
    def unverified_citations(self) -> list[str]:
        """Rule ids whose citation is not yet verified against the official document."""
        return sorted({n.rule_id for n in self.nodes if not n.citation.verified})
