"""Operational Safety Objectives.

SORA 2.5 defines 17 OSOs (#01-09, 13, 16-20, 23, 24). The design copy said "~24", which
is SORA 2.0; the count is always derived from the OSO table, never written down.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.common import Citation, ContainmentLevel, Robustness

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
    """Step #8's answer, computed from Tables 8 to 13 of AMC1 Article 11.

    S.4.8.1(c): "There are three possible levels of robustness for containment: low,
    medium and high." SORA 2.0's two-tier basic/enhanced is gone, and where a national
    AltMoC still uses those words it is an exemption rather than the method.

    ``level`` is ``None`` with ``assessment_required`` true in exactly two cases, and
    ``note`` says which: the tables answered "Out of scope", or an input Step #8 needs
    has not been supplied.
    """

    level: ContainmentLevel | None = None
    assessment_required: bool = True
    note: str = ""
    citation: Citation | None = None
