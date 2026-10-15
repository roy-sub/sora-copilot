"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

export const STAGES = ["Facts validated", "iGRC resolved", "Ground mitigations applied", "Airspace assessment", "SAIL and OSO set", "Containment check"];
const BUDGET = [210, 440, 180, 520, 260, 300];

export type StageState = "done" | "running" | "queued" | "failed";

/**
 * The engine's waiting state: named stages with per-stage elapsed time. The engine
 * itself is synchronous here; stages are paced so the run is legible, and the
 * result is the engine's own output.
 */
export function useStagedRun(active: boolean, onDone?: () => void, failAt?: number) {
  const [i, setI] = useState(active ? 0 : -1);
  const [ms, setMs] = useState<number[]>([]);
  const t0 = useRef(0);
  const done = useRef(onDone);
  done.current = onDone;

  useEffect(() => {
    if (!active) return;
    setI(0); setMs([]);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let stage = 0;
    let h: ReturnType<typeof setTimeout>;
    t0.current = performance.now();
    const next = () => {
      if (failAt === stage) return;
      const took = reduce ? 0 : BUDGET[stage];
      h = setTimeout(() => {
        setMs((m) => [...m, took]);
        stage++;
        setI(stage);
        if (stage < STAGES.length) next();
        else done.current?.();
      }, took);
    };
    next();
    return () => clearTimeout(h);
  }, [active, failAt]);

  const states: StageState[] = STAGES.map((_, k) => (k < i ? "done" : k === i ? (failAt === k ? "failed" : "running") : "queued"));
  return { states, ms, elapsed: ms.reduce((a, b) => a + b, 0), complete: i >= STAGES.length };
}

export function ComputationProgress({ states, ms, elapsed, note = "You can leave this page; the run continues." }: { states: StageState[]; ms: number[]; elapsed: number; note?: string }) {
  return (
    <div className="flex flex-col gap-4" role="status" aria-live="polite">
      <div className="flex flex-col gap-sheet">
        {STAGES.map((label, k) => {
          const s = states[k];
          return (
            <div key={label} className={cn("flex items-center gap-3 py-3 min-h-11", s === "running" && "border-l-2 border-accent pl-2.5", s === "failed" && "border-l-2 border-sail-6 pl-2.5", s === "queued" && "opacity-45")}
              style={s === "done" ? { animation: "stage-tick var(--t-ui) var(--ease-ui) both" } : undefined}>
              <span aria-hidden className={s === "done" || s === "running" ? "text-accent" : s === "failed" ? "text-sail-6" : ""}>{s === "done" ? "▣" : s === "running" ? "◧" : "□"}</span>
              <span className={cn("flex-1 t-data-13 leading-[1.3]", s === "queued" ? "text-ink-mid" : "text-ink-hi")}>{label}</span>
              <span className={cn("t-data-sm leading-none", s === "running" ? "text-ink-mid" : "text-ink-low")}>
                {s === "done" ? `${(ms[k] / 1000).toFixed(2)} s` : s === "running" ? "running" : s === "failed" ? "stopped" : "queued"}
              </span>
            </div>
          );
        })}
      </div>
      <p className="m-0 t-cap text-ink-low">Elapsed {(elapsed / 1000).toFixed(2)} s. {note}</p>
    </div>
  );
}
