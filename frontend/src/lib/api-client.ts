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
export type Sail = S["SAIL"];
export type Arc = S["ARC"];
export type Robustness = S["Robustness"];
export type GroundEnvironment = S["GroundEnvironment"];
export type AirspaceClass = S["AirspaceClass"];
export type OperationType = S["OperationType"];
// Not a named schema: FastAPI inlines the Literal, so take it from where it is used.
export type FittedMitigation = Drone["fitted_mitigations"][number];
export type OperationStatus = Operation["status"];
export type GeoJSONPolygon = S["GeoJSONPolygon"];

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

  rulebase: () => request<Rulebase>(`${V1}/rulebase/current`, { anonymous: true }),

  categoryCheck: (body: CategoryCheckIn) =>
    request<CategoryCheck>(`${V1}/public/category-check`, {
      method: "POST",
      body,
      anonymous: true,
    }),
} as const;
