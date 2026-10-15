"use client";

/**
 * One hook per endpoint, over TanStack Query.
 *
 * Query keys are arrays so a mutation can invalidate exactly what it changed. The rules
 * that matter:
 *
 * - A determination is invalidated by anything that changes the mission, because a
 *   determination computed from stale inputs is the one thing this product must not show.
 * - Counterfactuals are never cached across a mission change for the same reason: an
 *   offered suggestion that no longer applies is refused by the backend as stale.
 */

import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from "@tanstack/react-query";
import {
  api,
  type CategoryCheckIn,
  type DraftPatch,
  type DroneIn,
  type DronePatch,
  type OperationIn,
  type OperationPatch,
  type OrgPatch,
  type Sail,
} from "@/lib/api-client";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const keys = {
  health: ["health"] as const,
  org: ["org"] as const,
  rulebase: ["rulebase"] as const,
  drones: ["drones"] as const,
  operations: ["operations"] as const,
  operation: (id: string) => ["operations", id] as const,
  draft: (id: string) => ["operations", id, "draft"] as const,
  facts: (id: string) => ["operations", id, "facts"] as const,
  determination: (id: string) => ["operations", id, "determination"] as const,
  counterfactuals: (id: string) => ["operations", id, "counterfactuals"] as const,
  osos: (id: string) => ["operations", id, "osos"] as const,
  evidence: (id: string) => ["operations", id, "evidence"] as const,
  dossier: (id: string) => ["operations", id, "dossier"] as const,
};

/** True once there is a session to authenticate with, or auth is not configured. */
function useReady(): boolean {
  const { ready, session, configured } = useAuth();
  return ready && (!configured || Boolean(session));
}

type Opts<T> = Omit<UseQueryOptions<T, Error, T>, "queryKey" | "queryFn">;

export function useHealth(opts?: Opts<Awaited<ReturnType<typeof api.health>>>) {
  return useQuery({ queryKey: keys.health, queryFn: api.health, staleTime: 60_000, ...opts });
}

export function useRulebase() {
  // The rulebase changes only on deploy, so it is worth caching for the session.
  return useQuery({ queryKey: keys.rulebase, queryFn: api.rulebase, staleTime: Infinity });
}

export function useOrg() {
  const ready = useReady();
  return useQuery({ queryKey: keys.org, queryFn: api.org, enabled: ready });
}

export function useUpdateOrg() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: OrgPatch) => api.updateOrg(body),
    onSuccess: (org) => {
      qc.setQueryData(keys.org, org);
      // A rulebase pin changes which rulebase a determination runs against.
      qc.invalidateQueries({ queryKey: keys.operations });
    },
  });
}

export function useDrones() {
  const ready = useReady();
  return useQuery({ queryKey: keys.drones, queryFn: api.drones, enabled: ready });
}

export function useCreateDrone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DroneIn) => api.createDrone(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.drones }),
  });
}

export function useUpdateDrone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: DronePatch }) => api.updateDrone(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.drones });
      // An aircraft's dimensions pick the iGRC column, so every determination may move.
      qc.invalidateQueries({ queryKey: keys.operations });
    },
  });
}

export function useDeleteDrone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteDrone(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.drones }),
  });
}

export function useOperations() {
  const ready = useReady();
  return useQuery({ queryKey: keys.operations, queryFn: api.operations, enabled: ready });
}

export function useOperation(id: string | null) {
  const ready = useReady();
  return useQuery({
    queryKey: keys.operation(id ?? ""),
    queryFn: () => api.operation(id!),
    enabled: ready && Boolean(id),
  });
}

export function useCreateOperation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: OperationIn) => api.createOperation(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.operations }),
  });
}

export function useUpdateOperation(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: OperationPatch) => api.updateOperation(id, body),
    onSuccess: (op) => {
      qc.setQueryData(keys.operation(id), op);
      qc.invalidateQueries({ queryKey: keys.operations });
    },
  });
}

export function useDeleteOperation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteOperation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.operations }),
  });
}

export function useDraft(id: string | null) {
  const ready = useReady();
  return useQuery({
    queryKey: keys.draft(id ?? ""),
    queryFn: () => api.draft(id!),
    enabled: ready && Boolean(id),
  });
}

/** Everything that invalidates after the mission changes. */
function invalidateMission(qc: ReturnType<typeof useQueryClient>, id: string) {
  qc.invalidateQueries({ queryKey: keys.draft(id) });
  qc.invalidateQueries({ queryKey: keys.operation(id) });
  qc.invalidateQueries({ queryKey: keys.operations });
  // A stored determination is still valid — it is pinned to its own mission hash — but
  // the counterfactuals offered against the old mission are not.
  qc.removeQueries({ queryKey: keys.counterfactuals(id) });
}

export function usePatchDraft(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DraftPatch) => api.patchDraft(id, body),
    onSuccess: (draft) => {
      qc.setQueryData(keys.draft(id), draft);
      invalidateMission(qc, id);
    },
  });
}

export function useFacts(id: string | null) {
  const ready = useReady();
  return useQuery({
    queryKey: keys.facts(id ?? ""),
    queryFn: () => api.facts(id!),
    enabled: ready && Boolean(id),
  });
}

export function useConfirmFact(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (factId: string) => api.confirmFact(id, factId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.facts(id) });
      invalidateMission(qc, id);
    },
  });
}

export function useRejectFact(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (factId: string) => api.rejectFact(id, factId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.facts(id) });
      invalidateMission(qc, id);
    },
  });
}

export function useDetermination(id: string | null) {
  const ready = useReady();
  return useQuery({
    queryKey: keys.determination(id ?? ""),
    queryFn: () => api.determination(id!),
    enabled: ready && Boolean(id),
    // A 404 here means "not run yet", which is a state and not a failure.
    retry: (_n, error) => !(error instanceof ApiError),
  });
}

export function useRunDetermination(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (force: boolean = false) => api.determine(id, force),
    onSuccess: (determination) => {
      qc.setQueryData(keys.determination(id), determination);
      qc.invalidateQueries({ queryKey: keys.operation(id) });
      qc.invalidateQueries({ queryKey: keys.operations });
      qc.invalidateQueries({ queryKey: keys.counterfactuals(id) });
    },
  });
}

export function useCounterfactuals(id: string | null, opts?: { target_sail?: Sail | null; enabled?: boolean }) {
  const ready = useReady();
  return useQuery({
    queryKey: [...keys.counterfactuals(id ?? ""), opts?.target_sail ?? null],
    queryFn: () => api.counterfactuals(id!, { target_sail: opts?.target_sail ?? null }),
    enabled: ready && Boolean(id) && (opts?.enabled ?? true),
    // The search re-runs the engine for every candidate, so it is not cheap to repeat.
    staleTime: 5 * 60_000,
  });
}

export function useApplyCounterfactual(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (suggestionId: string) => api.applyCounterfactual(id, suggestionId),
    onSuccess: (draft) => {
      qc.setQueryData(keys.draft(id), draft);
      invalidateMission(qc, id);
    },
  });
}

export function useDeriveGeo(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.deriveGeo(id),
    onSuccess: () => invalidateMission(qc, id),
  });
}

export function useSampleDensity(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { density_per_km2: number; adjacent_area_populated?: boolean; source?: string }) =>
      api.sampleDensity(id, body),
    onSuccess: () => invalidateMission(qc, id),
  });
}

export function useIntakeChat(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => api.intakeChat(id, text),
    // New proposals are pending, which changes whether the determination can run.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.facts(id) });
      qc.invalidateQueries({ queryKey: keys.draft(id) });
      qc.invalidateQueries({ queryKey: keys.operation(id) });
    },
  });
}

export function useOsos(id: string | null) {
  const ready = useReady();
  return useQuery({
    queryKey: keys.osos(id ?? ""),
    queryFn: () => api.osos(id!),
    enabled: ready && Boolean(id),
    retry: (_n, error) => !(error instanceof ApiError),
  });
}

export function useEvidence(id: string | null) {
  const ready = useReady();
  return useQuery({
    queryKey: keys.evidence(id ?? ""),
    queryFn: () => api.evidence(id!),
    enabled: ready && Boolean(id),
  });
}

/**
 * Evidence upload goes through fetch directly rather than the JSON client: it is
 * multipart, and the client sets a JSON content type.
 */
export function useUploadEvidence(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, osoId }: { file: File; osoId?: string }) => {
      const { uploadEvidence } = await import("@/lib/upload");
      return uploadEvidence(id, file, osoId);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.evidence(id) });
      qc.invalidateQueries({ queryKey: keys.osos(id) });
      qc.invalidateQueries({ queryKey: keys.dossier(id) });
    },
  });
}

export function useDeleteEvidence(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (evidenceId: string) => api.deleteEvidence(id, evidenceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.evidence(id) });
      qc.invalidateQueries({ queryKey: keys.osos(id) });
      qc.invalidateQueries({ queryKey: keys.dossier(id) });
    },
  });
}

export function useDossierStatus(id: string | null) {
  const ready = useReady();
  return useQuery({
    queryKey: keys.dossier(id ?? ""),
    queryFn: () => api.dossierStatus(id!),
    enabled: ready && Boolean(id),
  });
}

export function useGenerateDossier(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (note?: string) => api.generateDossier(id, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.dossier(id) });
      qc.invalidateQueries({ queryKey: keys.operation(id) });
      qc.invalidateQueries({ queryKey: keys.operations });
    },
  });
}

export function useCategoryCheck() {
  return useMutation({ mutationFn: (body: CategoryCheckIn) => api.categoryCheck(body) });
}
