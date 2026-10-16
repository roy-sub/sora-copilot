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


#: Annex C Table C.1 writes every altitude row as "150 m (~500 ft) AGL": 150 m is the
#: figure, 500 ft the approximation of it. PLAN.md §0 had recorded the opposite reading
#: and used 152.4 m, which gave an operation between 150.0 m and 152.4 m the lower air
#: risk band. The adopted text settles it.
ALTITUDE_BAND_THRESHOLD_M = 150.0

#: Flight level 600, in metres AGL. Above it the airspace is AEC 11 and the initial ARC
#: is b. No specific-category operation reaches it, but the band exists in the table and
#: the engine is not in the business of leaving rows out.
FLIGHT_LEVEL_600_M = 18288.0

#: Annex C Table C.1 bands. The boundary is 150 m AGL, which the table writes as
#: "150 m (~500 ft)" — 150 m is the figure and 500 ft the approximation of it. FL 600
#: is the top of SORA's airspace: above it is AEC 11.
AltitudeBand = Literal["below_150m", "above_150m", "above_fl600"]

#: How each band is written wherever an operator reads it — the trace, the dossier, the
#: wizard. One definition, because a dossier that describes a different band from the one
#: the engine keyed on is the kind of inconsistency an authority notices.
ALTITUDE_BAND_LABELS: dict[str, str] = {
    "below_150m": "at or below 150 m (~500 ft) AGL",
    "above_150m": "above 150 m (~500 ft) AGL",
    "above_fl600": "above flight level 600",
}


def altitude_band_of(metres_agl: float) -> AltitudeBand:
    """Table C.1's own split. The single place the boundary is applied."""
    if metres_agl > FLIGHT_LEVEL_600_M:
        return "above_fl600"
    return "above_150m" if metres_agl > ALTITUDE_BAND_THRESHOLD_M else "below_150m"

EvidenceStatus = Literal["none", "claimed", "documented", "verified"]

FittedMitigation = Literal["parachute", "tether", "fts", "daa", "low_speed"]

#: Table 5 of AMC1 Article 11 names four ground mitigations. The identifiers below are
#: the ones stored since the first release and are kept so that determinations already
#: recorded keep meaning what they meant:
#:
#:   m1_strategic   M1(A) — strategic mitigations, sheltering
#:   m1_operational M1(B) — strategic mitigations, operational restrictions
#:   m1_ers         M1(C) — tactical mitigations, ground observation
#:   m2_impact      M2    — effects of UA impact dynamics are reduced
MitigationKind = Literal[
    "m1_strategic",
    "m1_operational",
    "m1_ers",
    "m2_impact",
    "strategic_air",
    "tactical_air",
]

#: Step #8 assesses outdoor assemblies within 1 km of the operational volume against
#: the bands in Tables 8 to 13.
AssemblySize = Literal["none", "under_40k", "40k_to_400k", "over_400k"]

#: S.4.8.1(c) of AMC1 Article 11: "There are three possible levels of robustness for
#: containment: low, medium and high." SORA 2.0's basic/enhanced pair is not this.
ContainmentLevel = Literal["low", "medium", "high"]

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
