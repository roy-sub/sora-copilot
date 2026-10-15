"use client";

// Client-side workspace state. Static export has no server, so everything the
// operator changes in the demo — evidence, re-runs, dossier versions, the
// wizard draft — persists to localStorage on this device only.

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { EVIDENCE, FLEET, OPERATIONS, type Aircraft, type Operation } from "@/data/fixtures";
import type { EvidenceState } from "@/components/Brand";
import type { OperationInput } from "@/engine/types";

export interface DossierVersion { v: number; note: string; rulebase: string; at: string }
export interface EvidenceFile { name: string; bytes: number }

interface State {
  /** Operator-made changes to fixture inputs (e.g. an applied counterfactual). */
  inputs: Record<string, OperationInput>;
  /** Operations created through the wizard. */
  created: Operation[];
  evidence: Record<string, Record<number, EvidenceState>>;
  files: Record<string, Record<number, EvidenceFile[]>>;
  dossiers: Record<string, DossierVersion[]>;
  rulebasePin: "pinned" | "latest";
  region: "frankfurt" | "dublin";
  /** Aircraft added on this device. */
  aircraft: Aircraft[];
}

const KEY = "sora.workspace.v1";

const initial: State = {
  inputs: {},
  created: [],
  evidence: EVIDENCE,
  files: {},
  dossiers: {
    "powerline-mur": [
      { v: 3, note: "OSO #08 evidence added", rulebase: "2026.2", at: "2 h ago" },
      { v: 2, note: "Altitude corrected to 118 m", rulebase: "2026.2", at: "Yesterday" },
      { v: 1, note: "First generation", rulebase: "2026.1", at: "12 Sep" },
    ],
  },
  rulebasePin: "pinned",
  region: "frankfurt",
  aircraft: [],
};

interface Api extends State {
  ready: boolean;
  operations: Operation[];
  fleet: Aircraft[];
  op: (id: string) => Operation | undefined;
  setInput: (id: string, input: OperationInput | null) => void;
  addOperation: (op: Operation) => void;
  setEvidence: (opId: string, oso: number, s: EvidenceState, files?: EvidenceFile[]) => void;
  addDossier: (opId: string, v: DossierVersion) => void;
  set: <K extends keyof State>(k: K, v: State[K]) => void;
  reset: () => void;
}

const Ctx = createContext<Api | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [s, setS] = useState<State>(initial);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setS({ ...initial, ...JSON.parse(raw) });
    } catch {}
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch {}
  }, [s, ready]);

  const operations = useMemo(
    () => [...s.created, ...OPERATIONS].map((o) => (s.inputs[o.id] ? { ...o, input: s.inputs[o.id] } : o)),
    [s.created, s.inputs],
  );

  const fleet = useMemo(() => [...FLEET, ...s.aircraft], [s.aircraft]);
  const op = useCallback((id: string) => operations.find((o) => o.id === id), [operations]);
  const setInput = useCallback((id: string, input: OperationInput | null) => setS((p) => {
    const inputs = { ...p.inputs };
    if (input) inputs[id] = input; else delete inputs[id];
    return { ...p, inputs };
  }), []);
  const addOperation = useCallback((o: Operation) => setS((p) => ({ ...p, created: [o, ...p.created.filter((x) => x.id !== o.id)] })), []);
  const setEvidence = useCallback((opId: string, oso: number, st: EvidenceState, files?: EvidenceFile[]) => setS((p) => ({
    ...p,
    evidence: { ...p.evidence, [opId]: { ...p.evidence[opId], [oso]: st } },
    files: files ? { ...p.files, [opId]: { ...p.files[opId], [oso]: files } } : p.files,
  })), []);
  const addDossier = useCallback((opId: string, v: DossierVersion) => setS((p) => ({ ...p, dossiers: { ...p.dossiers, [opId]: [v, ...(p.dossiers[opId] ?? [])] } })), []);
  const set = useCallback(<K extends keyof State>(k: K, v: State[K]) => setS((p) => ({ ...p, [k]: v })), []);
  const reset = useCallback(() => setS(initial), []);

  return (
    <Ctx.Provider value={{ ...s, ready, operations, fleet, op, setInput, addOperation, setEvidence, addDossier, set, reset }}>
      {children}
    </Ctx.Provider>
  );
}

export function useWorkspace() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useWorkspace outside WorkspaceProvider");
  return c;
}

/** OSO evidence state for an operation: absent = gap. */
export const evidenceOf = (ws: State, opId: string, num: number): EvidenceState => ws.evidence[opId]?.[num] ?? "gap";
