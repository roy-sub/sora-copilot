"""Request and response shapes for the API.

Separate from ``app/domain`` on purpose: the domain models are what the engine reasons
over, and they must not grow fields because an HTTP client found them convenient.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain import (
    ARC,
    SAIL,
    AirspaceClass,
    Citation,
    ContainmentRequirement,
    CounterfactualSuggestion,
    Country,
    FittedMitigation,
    GeoJSONPolygon,
    GroundEnvironment,
    OperationType,
    OsoRequirement,
    Robustness,
    TraceNode,
)

OperationStatus = Literal["draft", "determined", "dossier_ready", "submitted", "authorised"]


# ------------------------------------------------------------------ org


class OrgOut(BaseModel):
    id: UUID
    name: str
    country: Country
    plan: str
    data_region: Literal["frankfurt", "dublin"]
    rulebase_pin: str | None = None
    role: str = Field(description="The signed-in user's role in this organisation.")
    seats_used: int
    created_at: datetime


class MemberOut(BaseModel):
    user_id: UUID
    #: Copied from the verified JWT when they joined. Null for memberships created before
    #: migration 003, which the UI shows as "—" rather than inventing one.
    email: str | None = None
    role: Literal["owner", "admin", "member"]
    created_at: datetime
    #: True for the signed-in caller, so the UI can refuse to let them remove themselves.
    is_you: bool = False


class MemberPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["owner", "admin", "member"]


class InviteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    #: An invitation can never grant ownership. Transferring an organisation is a
    #: different act and is not built.
    role: Literal["admin", "member"] = "member"


class InviteOut(BaseModel):
    id: UUID
    email: str
    role: Literal["admin", "member"]
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    status: Literal["pending", "accepted", "expired"]


class SeatsOut(BaseModel):
    """Who is in the organisation, who has been invited, and how many seats remain."""

    members: list[MemberOut]
    invites: list[InviteOut]
    seats_used: int
    seats_limit: int
    #: Members plus pending invitations. A pending invitation holds a seat, or two
    #: people accepting at once would put the organisation over its plan.
    seats_committed: int
    can_invite: bool
    plan: str


class OrgPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    country: Country | None = None
    data_region: Literal["frankfurt", "dublin"] | None = None
    rulebase_pin: str | None = None
    operator_registration: str | None = None


# ------------------------------------------------------------------ drones


class DroneIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    registration: str | None = Field(default=None, max_length=60)
    max_dimension_m: float = Field(gt=0, le=100, description="Maximum characteristic dimension")
    mtom_kg: float = Field(gt=0, le=10_000)
    cruise_speed_ms: float = Field(ge=0, le=400)
    max_speed_ms: float = Field(gt=0, le=400)
    fitted_mitigations: list[FittedMitigation] = Field(default_factory=list)


class DronePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    registration: str | None = None
    max_dimension_m: float | None = Field(default=None, gt=0, le=100)
    mtom_kg: float | None = Field(default=None, gt=0, le=10_000)
    cruise_speed_ms: float | None = Field(default=None, ge=0, le=400)
    max_speed_ms: float | None = Field(default=None, gt=0, le=400)
    fitted_mitigations: list[FittedMitigation] | None = None


class DroneOut(BaseModel):
    id: UUID
    name: str
    registration: str | None = None
    max_dimension_m: float
    mtom_kg: float
    cruise_speed_ms: float
    max_speed_ms: float
    kinetic_energy_j: float = Field(description="½·m·v² at max speed. Computed, never entered.")
    fitted_mitigations: list[FittedMitigation]
    created_at: datetime


# ------------------------------------------------------------------ operations


class OperationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    site: str | None = Field(default=None, max_length=200)
    drone_id: UUID | None = None


class OperationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    site: str | None = None
    status: OperationStatus | None = None


class OperationOut(BaseModel):
    id: UUID
    name: str
    site: str | None = None
    status: OperationStatus
    drone_id: UUID | None = None
    mission: dict[str, Any] = Field(description="The wizard draft. Not a confirmed Mission.")
    created_at: datetime
    updated_at: datetime
    # Convenience so a dashboard row needs one request, not three.
    sail: SAIL | Literal["certified_category"] | None = None
    rulebase_version: str | None = None
    determined_at: datetime | None = None
    oso_gaps: int | None = None
    unconfirmed_facts: int = 0


# ------------------------------------------------------------------ wizard draft


class MissionVolumePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flight_geography: GeoJSONPolygon | None = None
    max_altitude_agl_m: float | None = Field(default=None, gt=0, le=10_000)
    duration_min: int | None = Field(default=None, gt=0, le=1440)


class MissionDraftPatch(BaseModel):
    """One wizard step's worth of the draft. Every field optional; nothing is required."""

    model_config = ConfigDict(extra="forbid")
    drone_id: UUID | None = None
    operation_type: OperationType | None = None
    volume: MissionVolumePatch | None = None
    ground_environment: GroundEnvironment | None = None
    population_density_per_km2: float | None = Field(default=None, ge=0)
    airspace_class: AirspaceClass | None = None
    near_aerodrome: bool | None = None
    controlled_airspace: bool | None = None
    atypical_airspace: bool | None = None
    country: Country | None = None
    mitigations: dict[str, Robustness] | None = None
    geo_zones: list[str] | None = None
    aerodrome_icao: str | None = None
    aerodrome_distance_km: float | None = Field(default=None, ge=0)


class DraftOut(BaseModel):
    operation_id: UUID
    mission: dict[str, Any]
    missing_fields: list[str] = Field(description="Required fields the draft does not carry yet.")
    unconfirmed_fields: list[str] = Field(description="Facts still waiting for confirmation.")
    ready_to_determine: bool


# ------------------------------------------------------------------ proposed facts


class ProposedFactOut(BaseModel):
    id: UUID
    field: str
    label: str = Field(description="The field, in the wizard's words.")
    value: Any
    confidence: float
    source_span: str | None = None
    status: Literal["pending", "confirmed", "rejected"]
    owning_step: str = Field(description="Which wizard step a rejection should return to.")


class IntakeChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=4000)


class IntakeChatOut(BaseModel):
    facts: list[ProposedFactOut]
    reply: str = Field(description="What was extracted, in prose. Never a conclusion.")
    model: str
    extractor: Literal["llm", "deterministic"] = Field(
        description="'deterministic' when no language-model key is configured."
    )


# ------------------------------------------------------------------ geo


class GeoDeriveOut(BaseModel):
    contingency_volume: GeoJSONPolygon
    ground_risk_buffer: GeoJSONPolygon
    adjacent_area: GeoJSONPolygon
    flight_geography_km2: float
    contingency_volume_km2: float
    ground_risk_buffer_km2: float
    adjacent_area_km2: float
    contingency_lateral_m: float
    contingency_vertical_m: float
    ground_risk_buffer_m: float
    adjacent_area_m: float
    derivations: list[dict[str, Any]] = Field(description="Each derived number and the rule behind it.")
    unverified: bool


class DensitySampleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    density_per_km2: float = Field(ge=0, le=1_000_000)
    adjacent_area_populated: bool = False
    source: str = Field(default="operator", max_length=120)


class DensitySampleOut(BaseModel):
    density_per_km2: float
    density_band: str
    suggested_environment: GroundEnvironment
    rationale: str
    raster_version: str
    adjacent_area_populated: bool
    is_suggestion_only: Literal[True] = Field(
        default=True,
        description="The engine never sees this until the operator confirms it.",
    )


# ------------------------------------------------------------------ determinations


class DeterminationOut(BaseModel):
    id: UUID
    operation_id: UUID
    rulebase_version: str
    mission_hash: str
    igrc: int | None
    final_grc: int | None
    initial_arc: ARC
    residual_arc: ARC
    sail: SAIL | Literal["certified_category"]
    tmpr: Literal["none", "low", "medium", "high"]
    osos: list[OsoRequirement]
    containment: ContainmentRequirement
    trace: list[TraceNode]
    warnings: list[str]
    computed_at: datetime
    is_verified: bool = Field(description="False while any table behind it is a seed.")
    oso_gaps: int
    freshly_computed: bool = Field(
        default=True, description="False when an identical run was already stored."
    )


class CounterfactualIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_sail: SAIL | None = None
    limit: int = Field(default=6, ge=1, le=20)


class CounterfactualOut(BaseModel):
    suggestions: list[CounterfactualSuggestion]
    current_sail: SAIL | Literal["certified_category"]


class ApplyCounterfactualIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    suggestion_id: str = Field(min_length=1, max_length=200)


# ------------------------------------------------------------------ OSO evidence


class OsoOut(BaseModel):
    oso_id: str
    title: str
    required_robustness: Robustness
    citation: Citation
    status: Literal["unmet", "claimed", "documented", "verified"]
    evidence: list[EvidenceOut] = Field(default_factory=list)
    what_it_requires: str
    checklist: list[str]


class EvidenceOut(BaseModel):
    id: UUID
    oso_id: str | None = None
    filename: str
    bytes: int | None = None
    content_type: str | None = None
    storage_path: str
    uploaded_at: datetime


class EvidenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    oso_id: str | None = Field(default=None, max_length=20)
    filename: str = Field(min_length=1, max_length=260)
    bytes: int = Field(ge=0, le=40 * 1024 * 1024)
    content_type: str | None = Field(default=None, max_length=120)


# ------------------------------------------------------------------ dossiers


class DossierOut(BaseModel):
    id: UUID
    operation_id: UUID
    determination_id: UUID | None = None
    version: int
    format: Literal["docx", "pdf"]
    storage_path: str
    note: str | None = None
    generated_at: datetime
    download_url: str | None = Field(
        default=None, description="Signed, short-lived. Absent when storage is not configured."
    )


class DossierIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    #: DOCX to edit alongside the authority's own forms, PDF to file. Both are rendered
    #: from one content path, so they cannot disagree.
    format: Literal["docx", "pdf"] = "docx"
    note: str | None = Field(default=None, max_length=300)


class DossierSectionOut(BaseModel):
    key: str
    name: str
    state: Literal["complete", "partial", "not_started"]
    meta: str


class DossierStatusOut(BaseModel):
    operation_id: UUID
    sections: list[DossierSectionOut]
    versions: list[DossierOut]
    next_version: int
    can_generate: bool
    blocker: str | None = None


# ------------------------------------------------------------------ rulebase


class RulebaseTableOut(BaseModel):
    name: str
    document: str
    section: str
    page: int | None = None
    rows: int
    verified: bool


class RulebaseOut(BaseModel):
    version: str
    is_current: bool
    tables: list[RulebaseTableOut]
    unverified_tables: list[str]
    verified: bool
    changelog: str
    sources_needed: list[str] = Field(
        description="Documents still required before the rulebase can be verified."
    )


# ------------------------------------------------------------------ public checker


class CategoryCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mass_band: Literal["sub250", "c_marked", "4to25", "over25"]
    ground_environment: GroundEnvironment
    operation_type: OperationType


class CategoryCheckOut(BaseModel):
    category: Literal["open", "specific", "certified"]
    subcategory: Literal["A1", "A2", "A3"] | None = None
    reason: str
    sail: SAIL | Literal["certified_category"] | None = None
    igrc: int | None = None
    initial_arc: ARC | None = None
    osos_required: int | None = None
    hint: str | None = None
    assumptions: list[str]
    rulebase_version: str
    is_verified: bool
    disclaimer: str


# ------------------------------------------------------------------ national packs


class PackItemOut(BaseModel):
    id: str
    kind: Literal["process", "form", "attachment", "contact", "note"]
    title: str
    detail: str
    min_sail: SAIL | None = None
    osos: list[str]
    url: str | None = None
    verified: bool
    source: str


class NationalPackOut(BaseModel):
    country: Literal["AT", "DE", "EU"]
    country_name: str
    authority: str
    authority_url: str | None = None
    summary: str
    complete: bool
    items: list[PackItemOut]
    unverified_ids: list[str]
    warning: str | None = None


class NationalCountryOut(BaseModel):
    country: Literal["AT", "DE", "EU"]
    country_name: str
    authority: str
    complete: bool
    items: int
    unverified: int


class SubmissionChecklistOut(BaseModel):
    """A country pack narrowed to one operation's SAIL and required OSOs."""

    operation_id: UUID
    country: Literal["AT", "DE", "EU"]
    country_name: str
    authority: str
    authority_url: str | None = None
    summary: str
    sail: SAIL | Literal["certified_category"] | None = None
    due: list[PackItemOut]
    pending: list[PackItemOut] = Field(
        description="Items this pack holds that are not due at the current SAIL."
    )
    evidence_attached: int = Field(description="Evidence files already uploaded for this operation.")
    dossier_versions: int
    warning: str | None = None
    disclaimer: str


# ------------------------------------------------------------------ billing


class PlanLimitsOut(BaseModel):
    """What a plan allows. `null` means unlimited; 0 means the feature is not included."""

    seats: int
    drones: int | None = None
    operations: int | None = None
    determinations_per_month: int | None = None
    dossiers_per_month: int | None = None
    evidence_files: int | None = None
    counterfactuals: bool
    conversational_intake: bool
    api_access: bool
    uses_dossier_credits: bool


class PlanOut(BaseModel):
    name: Literal["free", "per_dossier", "pro", "team", "consultancy"]
    label: str
    price_label: str
    limits: PlanLimitsOut
    #: Whether this deployment can actually sell it, i.e. has a Stripe price configured.
    purchasable: bool = False


class BillingStateOut(BaseModel):
    plan: PlanOut
    dossier_credits: int
    usage: dict[str, int]
    #: Set when a subscription exists, whatever its state.
    status: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    #: True when Stripe is configured on this deployment. False means nothing can be
    #: bought and the UI says so rather than offering a button that fails.
    billing_configured: bool
    #: True when the caller may open checkout or the portal at all.
    can_manage: bool
    plans: list[PlanOut]
    portal_available: bool


class CheckoutIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: Literal["pro", "team", "per_dossier"]
    #: Where to send the browser back to. Must be on the configured frontend origin.
    success_path: str = "/app/settings/?checkout=done"
    cancel_path: str = "/app/settings/?checkout=cancelled"


class CheckoutOut(BaseModel):
    url: str
    plan: str
    mode: Literal["subscription", "payment"]


class PortalOut(BaseModel):
    url: str


class WebhookOut(BaseModel):
    received: bool
    #: What the handler did, so a Stripe dashboard retry shows whether it was a no-op.
    outcome: Literal["applied", "ignored", "duplicate"]


OsoOut.model_rebuild()
