"use client";

/**
 * The typed API surface, generated from the backend's OpenAPI schema.
 *
 * Types come from `api-types.ts`, which `npm run gen:api` regenerates from
 * `backend/openapi.json`. Nothing here restates a shape by hand, so the client cannot
 * drift from FastAPI: if the backend changes a field, this file stops type-checking.
 */

import { request, type Problem } from "@/lib/api";
import type { components } from "@/lib/api-types";

type S = components["schemas"];

export type Org = S["OrgOut"];
export type OrgPatch = S["OrgPatch"];
export type Drone = S["DroneOut"];
export type DroneIn = S["DroneIn"];
export type DronePatch = S["DronePatch"];
export type Operation = S["OperationOut"];
export type OperationIn = S["OperationIn"];
export type OperationPatch = S["OperationPatch"];
export type Draft = S["DraftOut"];
export type DraftPatch = S["MissionDraftPatch"];
export type ProposedFact = S["ProposedFactOut"];
export type Determination = S["DeterminationOut"];
export type TraceNode = S["TraceNode"];
export type OsoRequirement = S["OsoRequirement"];
export type Citation = S["Citation"];
export type Counterfactual = S["CounterfactualSuggestion"];
export type CounterfactualChange = S["CounterfactualChange"];
export type CounterfactualResult = S["CounterfactualOut"];
export type GeoDerive = S["GeoDeriveOut"];
export type DensitySample = S["DensitySampleOut"];
export type Rulebase = S["RulebaseOut"];
export type CategoryCheckIn = S["CategoryCheckIn"];
export type CategoryCheck = S["CategoryCheckOut"];
export type Health = S["Health"];
export type IntakeChat = S["IntakeChatOut"];
export type Oso = S["OsoOut"];
export type Evidence = S["EvidenceOut"];
export type Dossier = S["DossierOut"];
export type DossierStatus = S["DossierStatusOut"];
export type DossierSection = S["DossierSectionOut"];
export type DossierFormat = Dossier["format"];
export type Extractor = IntakeChat["extractor"];
export type Sail = S["SAIL"];
export type Arc = S["ARC"];
export type Robustness = S["Robustness"];
export type GroundEnvironment = S["GroundEnvironment"];
export type AirspaceClass = S["AirspaceClass"];
export type OperationType = S["OperationType"];
// Not a named schema: FastAPI inlines the Literal, so take it from where it is used.
export type FittedMitigation = Drone["fitted_mitigations"][number];
export type OperationStatus = Operation["status"];
export type Country = Org["country"];
export type DataRegion = Org["data_region"];
export type GeoJSONPolygon = S["GeoJSONPolygon"];
export type BillingState = S["BillingStateOut"];
export type Seats = S["SeatsOut"];
export type Member = S["MemberOut"];
export type Invite = S["InviteOut"];
export type MemberRole = Member["role"];
export type InviteRole = S["InviteIn"]["role"];
export type PlanSummary = S["PlanOut"];
export type PlanLimits = S["PlanLimitsOut"];
export type PlanName = PlanSummary["name"];
export type CheckoutResult = S["CheckoutOut"];
export type NationalPack = S["NationalPackOut"];
export type NationalCountry = S["NationalCountryOut"];
export type SubmissionChecklist = S["SubmissionChecklistOut"];
export type PackItem = S["PackItemOut"];

export type { Problem };

const V1 = "/api/v1";

/** The SAIL ramp, in order, so a UI can compare two of them. */
export const SAIL_ORDER: readonly (Sail | "certified_category")[] = [
  "I",
  "II",
  "III",
  "IV",
  "V",
  "VI",
  "certified_category",
];

export const sailIndex = (s: Sail | "certified_category" | null | undefined): number =>
  s ? SAIL_ORDER.indexOf(s) + 1 : 0;

/** Roman numeral → 1–6, for the SailBadge. Null for the certified category. */
export const sailLevel = (s: Sail | "certified_category" | null | undefined): 1 | 2 | 3 | 4 | 5 | 6 | null => {
  const i = SAIL_ORDER.indexOf(s as Sail);
  return i >= 0 && i < 6 ? ((i + 1) as 1 | 2 | 3 | 4 | 5 | 6) : null;
};

export const api = {
  health: () => request<Health>("/healthz", { anonymous: true }),

  session: () => request<Org>(`${V1}/auth/session`, { method: "POST" }),
  org: () => request<Org>(`${V1}/orgs/me`),
  updateOrg: (body: OrgPatch) => request<Org>(`${V1}/orgs/me`, { method: "PATCH", body }),

  drones: () => request<Drone[]>(`${V1}/drones`),
  createDrone: (body: DroneIn) => request<Drone>(`${V1}/drones`, { method: "POST", body }),
  updateDrone: (id: string, body: DronePatch) =>
    request<Drone>(`${V1}/drones/${id}`, { method: "PATCH", body }),
  deleteDrone: (id: string) => request<void>(`${V1}/drones/${id}`, { method: "DELETE" }),

  operations: () => request<Operation[]>(`${V1}/operations`),
  operation: (id: string) => request<Operation>(`${V1}/operations/${id}`),
  createOperation: (body: OperationIn) =>
    request<Operation>(`${V1}/operations`, { method: "POST", body }),
  updateOperation: (id: string, body: OperationPatch) =>
    request<Operation>(`${V1}/operations/${id}`, { method: "PATCH", body }),
  deleteOperation: (id: string) => request<void>(`${V1}/operations/${id}`, { method: "DELETE" }),

  draft: (id: string) => request<Draft>(`${V1}/operations/${id}/draft`),
  patchDraft: (id: string, body: DraftPatch) =>
    request<Draft>(`${V1}/operations/${id}/draft`, { method: "PATCH", body }),

  facts: (id: string) => request<ProposedFact[]>(`${V1}/operations/${id}/facts`),
  confirmFact: (id: string, factId: string) =>
    request<ProposedFact>(`${V1}/operations/${id}/facts/${factId}/confirm`, { method: "POST" }),
  rejectFact: (id: string, factId: string) =>
    request<ProposedFact>(`${V1}/operations/${id}/facts/${factId}/reject`, { method: "POST" }),

  determine: (id: string, force = false) =>
    request<Determination>(`${V1}/operations/${id}/determine${force ? "?force=true" : ""}`, {
      method: "POST",
    }),
  determination: (id: string) => request<Determination>(`${V1}/operations/${id}/determination`),

  counterfactuals: (id: string, body: { target_sail?: Sail | null; limit?: number } = {}) =>
    request<CounterfactualResult>(`${V1}/operations/${id}/counterfactual`, { method: "POST", body }),
  applyCounterfactual: (id: string, suggestionId: string) =>
    request<Draft>(`${V1}/operations/${id}/counterfactual/apply`, {
      method: "POST",
      body: { suggestion_id: suggestionId },
    }),

  deriveGeo: (id: string) => request<GeoDerive>(`${V1}/operations/${id}/geo/derive`, { method: "POST" }),
  sampleDensity: (
    id: string,
    body: { density_per_km2: number; adjacent_area_populated?: boolean; source?: string },
  ) => request<DensitySample>(`${V1}/operations/${id}/geo/density`, { method: "POST", body }),

  intakeChat: (id: string, text: string) =>
    request<IntakeChat>(`${V1}/operations/${id}/intake/chat`, { method: "POST", body: { text } }),

  osos: (id: string) => request<Oso[]>(`${V1}/operations/${id}/osos`),
  evidence: (id: string) => request<Evidence[]>(`${V1}/operations/${id}/evidence`),
  deleteEvidence: (id: string, evidenceId: string) =>
    request<void>(`${V1}/operations/${id}/evidence/${evidenceId}`, { method: "DELETE" }),

  dossierStatus: (id: string) => request<DossierStatus>(`${V1}/operations/${id}/dossier`),
  generateDossier: (id: string, format: DossierFormat = "docx", note?: string) =>
    request<Dossier>(`${V1}/operations/${id}/dossier`, {
      method: "POST",
      body: { format, note: note ?? null },
    }),

  rulebase: () => request<Rulebase>(`${V1}/rulebase/current`, { anonymous: true }),

  workedExample: () => request<Operation | null>(`${V1}/demo/example`),
  seedWorkedExample: () => request<Operation>(`${V1}/demo/example`, { method: "POST" }),

  seats: () => request<Seats>(`${V1}/orgs/me/seats`),
  invite: (email: string, role: InviteRole = "member") =>
    request<Seats>(`${V1}/orgs/me/invites`, { method: "POST", body: { email, role } }),
  revokeInvite: (id: string) =>
    request<Seats>(`${V1}/orgs/me/invites/${id}`, { method: "DELETE" }),
  removeMember: (userId: string) =>
    request<Seats>(`${V1}/orgs/me/members/${userId}`, { method: "DELETE" }),
  setMemberRole: (userId: string, role: MemberRole) =>
    request<Seats>(`${V1}/orgs/me/members/${userId}`, { method: "PATCH", body: { role } }),

  billing: () => request<BillingState>(`${V1}/billing`),
  checkout: (plan: "pro" | "team" | "per_dossier") =>
    request<CheckoutResult>(`${V1}/billing/checkout`, {
      method: "POST",
      body: {
        plan,
        success_path: "/app/settings/?checkout=done",
        cancel_path: "/app/settings/?checkout=cancelled",
      },
    }),
  billingPortal: () => request<{ url: string }>(`${V1}/billing/portal`, { method: "POST" }),

  countries: () => request<NationalCountry[]>(`${V1}/national`, { anonymous: true }),
  nationalPack: (code: string) =>
    request<NationalPack>(`${V1}/national/${code}`, { anonymous: true }),
  submissionChecklist: (id: string) =>
    request<SubmissionChecklist>(`${V1}/national/operations/${id}/checklist`),

  categoryCheck: (body: CategoryCheckIn) =>
    request<CategoryCheck>(`${V1}/public/category-check`, {
      method: "POST",
      body,
      anonymous: true,
    }),
  /** Download URLs. The browser follows these itself, with the token appended by the
   *  caller via `withToken`, because a <a download> cannot carry a header. */
  evidenceDownloadPath: (id: string, evidenceId: string) =>
    `${V1}/operations/${id}/evidence/${evidenceId}/download`,
  dossierDownloadPath: (id: string, dossierId: string) =>
    `${V1}/operations/${id}/dossier/${dossierId}/download`,
} as const;
