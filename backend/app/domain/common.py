"""Vocabulary shared by every layer: enums, citations, GeoJSON.

These names are the operator's own — iGRC, GRC, ARC, residual ARC, SAIL, OSO. They are
never softened into "score" or "level", in code or in anything the user reads.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class OperationType(StrEnum):
    VLOS = "vlos"
    EVLOS = "evlos"
    BVLOS = "bvlos"


class GroundEnvironment(StrEnum):
    CONTROLLED = "controlled_ground_area"
    SPARSELY_POPULATED = "sparsely_populated"
    POPULATED = "populated"
    ASSEMBLY = "assembly_of_people"


class AirspaceClass(StrEnum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"


class Robustness(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SAIL(StrEnum):
    I = "I"  # noqa: E741 — the regulation's own label
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"
    VI = "VI"


class ARC(StrEnum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"


class Country(StrEnum):
    AT = "AT"
    DE = "DE"
    EU = "EU"


#: SORA keys the air-risk tree on 500 ft AGL, which is 152.4 m — not the round 150 m the
#: design copy used. PLAN.md §0 records the decision to use the regulation's threshold
#: and relabel the UI "above 500 ft (152 m)".
ALTITUDE_BAND_THRESHOLD_M = 152.4

AltitudeBand = Literal["below_500ft", "above_500ft"]

EvidenceStatus = Literal["none", "claimed", "documented", "verified"]

FittedMitigation = Literal["parachute", "tether", "fts", "daa", "low_speed"]

MitigationKind = Literal["m1_strategic", "m1_ers", "m2_impact", "strategic_air", "tactical_air"]

TraceNodeKind = Literal["fact", "rule", "override", "default"]


#: The one sentence that must appear on every verdict, every export and the free
#: checker. Defined here so there is a single wording rather than one per surface.
DISCLAIMER = (
    "SORA Copilot prepares and verifies your risk assessment. Your national aviation "
    "authority grants the authorisation."
)


class Citation(BaseModel):
    """Where a value came from. A conclusion without one is a bug, not a degraded result."""

    model_config = ConfigDict(frozen=True)

    document: str = Field(description='e.g. "JARUS SORA 2.5 main body"')
    section: str = Field(description='e.g. "Table 2 — intrinsic GRC"')
    page: int | None = None
    url: str | None = None
    verified: bool = Field(
        default=False,
        description=(
            "False while the value is transcribed from the seed rather than the official "
            "document. Surfaced to the user as UNVERIFIED, never hidden."
        ),
    )


class GeoJSONPolygon(BaseModel):
    """A GeoJSON Polygon in EPSG:4326. Area and buffer maths reproject to an equal-area CRS."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[Annotated[list[float], Field(min_length=2, max_length=3)]]] = Field(
        description="Rings of [lon, lat] (optionally [lon, lat, alt]); the first ring is the exterior."
    )
