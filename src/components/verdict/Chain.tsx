"use client";

import { useEffect, useState } from "react";
import { roman } from "@/engine/engine";
import type { Determination } from "@/engine/types";

/** figure-count: numerals count up once per determination, never again. */
function useCountOnce(target: number | null, run: boolean) {
  const [v, setV] = useState(run && target != null ? 0 : target);
  useEffect(() => {
    if (!run || target == null || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setV(target); return; }
    const t0 = performance.now();
    let raf = 0;
    const ease = (x: number) => 1 - Math.pow(1 - x, 4);
    const step = (t: number) => {
      const p = Math.min(1, (t - t0) / 900);
      setV(Math.round(ease(p) * target));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);
  return run ? v : target;
}

export function chainLinks(d: Determination, notes: { igrc: string; grc: string; arc: string; rarc: string }) {
  return [
    { k: "iGRC", n: d.igrc, v: d.igrc == null ? "—" : String(d.igrc), note: notes.igrc },
    { k: "GRC", n: d.grc, v: d.grc == null ? "—" : String(d.grc), note: notes.grc },
    { k: "ARC", n: null, v: d.initialArc, note: notes.arc },
    { k: "Residual ARC", n: null, v: d.residualArc, note: notes.rarc },
    { k: "SAIL", n: null, v: d.outcome.kind === "sail" ? roman(d.outcome.sail) : "Cert.", note: d.outcome.kind === "sail" ? "GRC × residual ARC" : "Certified category" },
  ];
}

function Cell({ k, n, v, note, i, count, recomputing }: { k: string; n: number | null; v: string; note: string; i: number; count: boolean; recomputing?: boolean }) {
  const c = useCountOnce(n, count);
  return (
    <div className="flex-[1_1_46%] md:flex-[1_1_132px] min-w-0" style={{ animation: `chain-link var(--t-panel) var(--ease-ui) ${i * 90}ms both` }}>
      <div className="bg-sheet-well px-4 py-3.5 min-w-[132px] flex flex-col gap-[5px] h-full box-border">
        <span className="t-micro text-ink-low">{k}</span>
        <span className={`text-[28px] font-bold leading-none tracking-[-.02em] tnum ${recomputing ? "text-ink-low" : "text-ink-hi"}`}>{n != null ? c : v}</span>
        <span className="text-[11px] leading-[1.35] text-ink-low">{recomputing ? "re-running" : note}</span>
      </div>
    </div>
  );
}

export function RiskChainReadout({ links, countUp, recomputing }: { links: ReturnType<typeof chainLinks>; countUp: boolean; recomputing?: boolean }) {
  return (
    <div className="flex gap-sheet flex-wrap bg-hairline">
      {links.map((l, i) => <Cell key={l.k} {...l} i={i} count={countUp} recomputing={recomputing} />)}
    </div>
  );
}
