"""Operational Safety Objectives.

SORA 2.5 defines 17 OSOs (#01-09, 13, 16-20, 23, 24). The design copy said "~24", which
is SORA 2.0; the count is always derived from the OSO table, never written down.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.common import Citation, Robustness

OsoStatus = Literal["unmet", "claimed", "documented", "verified"]


class OsoRequirement(BaseModel):
    oso_id: str = Field(description='e.g. "OSO#05"')
    title: str
    required_robustness: Robustness
    citation: Citation
    status: OsoStatus = "unmet"

    @property
    def is_required(self) -> bool:
        return self.required_robustness is not Robustness.NONE

    @property
    def is_gap(self) -> bool:
        return self.is_required and self.status == "unmet"


class ContainmentRequirement(BaseModel):
    """Containment is computed from the transcribed containment table.

    Until that table is verified against the official text the level stays ``None`` and
    ``assessment_required`` is true, so the UI says "assessment required" rather than
    showing a number we cannot source.
    """

    level: Literal["basic", "enhanced"] | None = None
    assessment_required: bool = True
    note: str = ""
    citation: Citation | None = None
