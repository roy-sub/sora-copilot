"""The mission: everything the operator tells us, before the engine sees any of it.

A ``Mission`` is only assembled from facts the operator has explicitly confirmed. The
LLM contributes ``ProposedFact`` objects, which are inert until confirmed; there is no
code path from a pending fact to the engine (build spec §4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.common import (
    AirspaceClass,
    AltitudeBand,
    AssemblySize,
    Country,
    EvidenceStatus,
    FittedMitigation,
    GeoJSONPolygon,
    GroundEnvironment,
    MitigationKind,
    OperationType,
    Robustness,
    altitude_band_of,
)


class Drone(BaseModel):
    id: UUID
    name: str
    max_dimension_m: float = Field(gt=0, description="Maximum characteristic dimension")
    mtom_kg: float = Field(gt=0)
    cruise_speed_ms: float = Field(ge=0)
    max_speed_ms: float = Field(gt=0)
    kinetic_energy_j: float | None = Field(
        default=None, description="½·m·v² at max speed. Computed when absent; never hand-entered."
    )
    fitted_mitigations: list[FittedMitigation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _derive_kinetic_energy(self) -> Drone:
        if self.kinetic_energy_j is None:
            object.__setattr__(self, "kinetic_energy_j", 0.5 * self.mtom_kg * self.max_speed_ms**2)
        return self


class OperationalVolume(BaseModel):
    flight_geography: GeoJSONPolygon
    contingency_volume: GeoJSONPolygon | None = Field(
        default=None, description="Derived by services.geo from altitude and speed; user-adjustable."
    )
    ground_risk_buffer: GeoJSONPolygon | None = Field(
        default=None, description="Derived by services.geo; user-adjustable."
    )
    max_altitude_agl_m: float = Field(gt=0)
    adjacent_area_km: float = Field(
        default=0.0, ge=0, description="Derived from altitude and speed, not entered."
    )

    @property
    def altitude_band(self) -> AltitudeBand:
        """Annex C Table C.1's own split: 150 m AGL, and FL 600 above it."""
        return altitude_band_of(self.max_altitude_agl_m)


class MitigationClaim(BaseModel):
    kind: MitigationKind
    robustness: Robustness
    evidence_status: EvidenceStatus = "none"
    notes: str | None = None


class Mission(BaseModel):
    """A complete, confirmed mission. The only thing ``engine.facts`` is allowed to read."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    org_id: UUID
    drone_id: UUID
    operation_type: OperationType
    volume: OperationalVolume
    ground_environment: GroundEnvironment
    population_density_per_km2: float | None = Field(
        default=None,
        ge=0,
        description="Sampled from the density raster, always confirmed or overridden by the operator.",
    )
    airspace_class: AirspaceClass
    near_aerodrome: bool
    altitude_band: AltitudeBand
    controlled_airspace: bool
    atypical_airspace: bool
    transponder_mandatory_zone: bool = Field(
        default=False,
        description=(
            "A Mode-S Veil or transponder mandatory zone. Annex C Table C.1 makes this "
            "its own category at both altitude bands — AEC 2 above 150 m and AEC 7 below "
            "— so without it a TMZ operation is scored as ordinary uncontrolled airspace."
        ),
    )
    demonstrated_air_density_rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description=(
            "What the operator has demonstrated the LOCAL air traffic density to be, on "
            "Table C.1's 1-to-5 scale. Table C.2 buys a lower residual ARC only in "
            "exchange for this demonstration, so without it a claimed strategic air "
            "mitigation earns no reduction."
        ),
    )
    adjacent_area_density_per_km2: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Average population density between the outer limit of the ground risk "
            "buffer and the outer limit of the adjacent ground area (Step #8). One of "
            "the two inputs that select a column in Tables 8 to 13."
        ),
    )
    adjacent_assembly_size: AssemblySize | None = Field(
        default=None,
        description=(
            "The largest outdoor assembly expected within 1 km of the operational volume "
            "while the flight takes place. The other column input for Tables 8 to 13."
        ),
    )
    sheltering_applicable: bool | None = Field(
        default=None,
        description=(
            "Whether people in the adjacent ground area are sheltered by structures the "
            "UA is not expected to penetrate. Only a 3 m UA needs an answer: Table 8 "
            "assumes sheltering applies below that, and Tables 11 to 13 assume it does "
            "not from 8 m up."
        ),
    )
    mitigations: list[MitigationClaim] = Field(default_factory=list)
    country: Country = Country.AT

    def mitigation(self, kind: MitigationKind) -> MitigationClaim | None:
        return next((m for m in self.mitigations if m.kind == kind), None)


class ProposedFact(BaseModel):
    """A candidate fact the LLM extracted from prose. Inert by construction.

    ``status`` leaves ``pending`` only through an explicit user action on
    ``POST /operations/{id}/facts/{fact_id}/confirm``. The determination service reads
    confirmed facts and nothing else.
    """

    id: UUID
    operation_id: UUID
    field: str = Field(description="Dotted path into Mission, e.g. 'volume.max_altitude_agl_m'")
    value: object
    confidence: float = Field(ge=0, le=1)
    source_span: str | None = Field(
        default=None, description="The span of the operator's own words this came from."
    )
    status: Literal["pending", "confirmed", "rejected"] = "pending"
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None
