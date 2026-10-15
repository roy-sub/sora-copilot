"""The determination: what the rules engine concluded, and why.

Produced only by ``app.engine.runner``. Carries a pinned ``rulebase_version`` and a
complete trace; both are part of the record, not metadata.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from app.domain.common import ARC, SAIL
from app.domain.oso import ContainmentRequirement, OsoRequirement
from app.domain.trace import TraceNode

#: An operation whose final GRC exceeds 7 leaves SORA entirely and needs the certified
#: category. It is an outcome, not an error.
CertifiedCategory = Literal["certified_category"]

Tmpr = Literal["none", "low", "medium", "high"]


class Determination(BaseModel):
    id: UUID
    operation_id: UUID
    rulebase_version: str = Field(description="Pinned at computation time; never back-filled.")
    mission_hash: str = Field(
        default="",
        description="sha256 of the canonical confirmed Mission; makes re-running idempotent.",
    )

    # Deliberate deviation from the build spec's `igrc: int`. When an operation is
    # outside SORA — an aircraft beyond the last iGRC column, or a combination the table
    # leaves blank — there is no intrinsic ground risk class. Reporting 0 would invent a
    # value the regulation does not define, which is the one thing this product must not
    # do, so the absence is modelled as absence.
    igrc: int | None = None
    final_grc: int | None = None
    initial_arc: ARC
    residual_arc: ARC
    sail: SAIL | CertifiedCategory
    osos: list[OsoRequirement] = Field(default_factory=list)
    containment: ContainmentRequirement
    tmpr: Tmpr = "none"
    trace: list[TraceNode] = Field(default_factory=list)
    warnings: list[str] = Field(
        default_factory=list,
        description="Carries every UNVERIFIED table that fed this determination. Shown, not logged.",
    )
    computed_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_certified_category(self) -> bool:
        return self.sail == "certified_category"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def oso_gaps(self) -> int:
        return sum(1 for o in self.osos if o.is_gap)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_verified(self) -> bool:
        """True only when every table behind this determination is verified."""
        return not self.warnings


class CounterfactualChange(BaseModel):
    """One parameter moved, and what claiming it would cost."""

    field: str = Field(description="Dotted Mission path the change applies to.")
    from_value: object
    to_value: object
    label: str = Field(description="The change, in the operator's words.")
    evidence_required: str = Field(description="What the new level demands as evidence.")
    effort_cost: float = Field(description="From tables/cf_costs.csv; used only to rank.")


class CounterfactualSuggestion(BaseModel):
    """A minimal set of changes that lowers SAIL.

    The build spec's model carried one ``field``/``from_value``/``to_value``. It is a list
    here because single-parameter search genuinely misses real answers: reaching a lower
    SAIL often needs a ground-risk reduction AND an air-risk reduction together, and an
    advisor that reports "nothing helps" in that case is worse than no advisor. The
    singular fields are kept as read-only conveniences for the common one-change case.
    """

    id: str
    title: str = Field(description="The change or changes, in the operator's words.")
    changes: list[CounterfactualChange] = Field(min_length=1)
    resulting_sail: SAIL | CertifiedCategory
    chain_effect: str = Field(description='e.g. "GRC 5 → 4 · residual ARC c → b"')
    oso_delta: list[str] = Field(
        default_factory=list, description="OSOs added, removed or re-levelled by the change."
    )
    evidence_required: str = Field(description="Everything the new levels demand as evidence.")
    effort_cost: float = Field(description="Total effort cost; used only to rank.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def change_count(self) -> int:
        return len(self.changes)

    @property
    def field(self) -> str:
        """The single change's field. Only meaningful when ``change_count`` is 1."""
        return self.changes[0].field

    @property
    def from_value(self) -> object:
        return self.changes[0].from_value

    @property
    def to_value(self) -> object:
        return self.changes[0].to_value
