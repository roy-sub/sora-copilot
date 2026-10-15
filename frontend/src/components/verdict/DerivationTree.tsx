"use client";

import { useState } from "react";
import { CitationChip } from "@/components/Brand";
import { SailBadge, SailPlaceholder } from "@/components/SailBadge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import type { Determination, TraceNode } from "@/engine/types";

// Fixed 960×520 canvas: five fact leaves → iGRC / ARC → GRC / residual ARC → SAIL.
const POS: Record<string, { left: number; top: number; w: number; delay: number }> = {
  "f-dim": { left: 0, top: 20, w: 200, delay: 60 },
  "f-ground": { left: 0, top: 120, w: 200, delay: 120 },
  "f-alt": { left: 0, top: 220, w: 200, delay: 180 },
  "f-airspace": { left: 0, top: 312, w: 200, delay: 240 },
  "f-aerodrome": { left: 0, top: 412, w: 200, delay: 300 },
  "n-igrc": { left: 250, top: 70, w: 190, delay: 460 },
  "n-arc": { left: 250, top: 350, w: 190, delay: 480 },
  "n-grc": { left: 510, top: 70, w: 190, delay: 700 },
  "n-rarc": { left: 510, top: 350, w: 190, delay: 720 },
  "root-sail": { left: 770, top: 180, w: 190, delay: 1020 },
};

const EDGES: { d: string; len: number; delay: number; accent?: boolean; dur?: number }[] = [
  { d: "M200,56 C225,56 225,118 250,118", len: 140, delay: 0 },
  { d: "M200,156 C225,156 225,118 250,118", len: 140, delay: 60 },
  { d: "M200,256 C230,256 230,398 250,398", len: 220, delay: 120 },
  { d: "M200,338 C230,338 230,398 250,398", len: 160, delay: 180 },
  { d: "M200,438 C230,438 230,398 250,398", len: 160, delay: 240 },
  { d: "M440,118 L510,118", len: 80, delay: 420, dur: 420 },
  { d: "M440,398 L510,398", len: 80, delay: 480, dur: 420 },
  { d: "M700,118 C735,118 735,260 770,260", len: 220, delay: 760, accent: true },
  { d: "M700,398 C735,398 735,260 770,260", len: 220, delay: 820, accent: true },
];

const settle = (delay: number) => ({ animation: `node-settle 240ms var(--ease-ui) ${delay}ms both` });

function Inspector({ nodes, byId, onClose }: { nodes: TraceNode[]; byId: Map<string, TraceNode>; onClose: (id: string) => void }) {
  if (!nodes.length) return <p className="m-0 mt-3 t-cap text-ink-low">Select a node to see the rule, its inputs and the lookup.</p>;
  return (
    <div className="mt-3 grid gap-sheet bg-hairline border border-hairline grid-cols-[repeat(auto-fit,minmax(260px,1fr))]">
      {nodes.map((n) => (
        <div key={n.id} className="bg-sheet-well p-4 flex flex-col gap-2.5 animate-[node-settle_240ms_var(--ease-ui)_both]">
          <div className="flex items-baseline justify-between gap-3">
            <span className="t-micro text-ink-low">{n.term} · rule fired</span>
            <button type="button" aria-label={`Collapse ${n.term}`} onClick={() => onClose(n.id)} className="size-8 -m-1.5 bg-transparent border-0 text-ink-low hover:text-ink-hi">✕</button>
          </div>
          <p className="m-0 t-body-sm text-ink-hi pretty">{n.rule}</p>
          {n.citation && <CitationChip reference={n.citation} size="md" />}
          <div className="flex flex-col gap-1">
            <span className="t-micro-10 text-ink-low">Inputs</span>
            {n.inputs.map((i) => { const x = byId.get(i); return x && <span key={i} className="t-data-sm text-ink-mid">{x.kind === "fact" ? x.rule : `${x.term} ${x.value}`}</span>; })}
            {n.detail?.map((l) => <span key={l} className="t-data-sm text-ink-low">{l}</span>)}
          </div>
        </div>
      ))}
    </div>
  );
}

export function DerivationTree({ d, changed, runKey, onReplay }: { d: Determination; changed: Set<string>; runKey: number; onReplay: () => void }) {
  const byId = new Map(d.trace.map((n) => [n.id, n]));
  const [open, setOpen] = useState<string[]>(["n-igrc", "n-grc", "n-arc"]);
  const toggle = (id: string) => setOpen((o) => (o.includes(id) ? o.filter((x) => x !== id) : [...o, id]));
  const sail = d.outcome.kind === "sail" ? d.outcome.sail : null;

  const node = (id: string) => {
    const n = byId.get(id)!;
    const p = POS[id];
    const isOpen = open.includes(id);
    const band = changed.has(id) ? "shadow-[inset_2px_0_0_var(--accent)]" : "";
    if (n.kind === "fact")
      return (
        <div key={id} className={cn("absolute p-3 bg-sheet border border-hairline box-border", band)} style={{ left: p.left, top: p.top, width: p.w, ...settle(p.delay) }}>
          <span className="t-micro-10 text-ink-low">Fact</span>
          <div className="mt-1.5 t-data-13 leading-[1.35] text-ink-hi">{n.rule}</div>
        </div>
      );
    if (n.kind === "root")
      return (
        <div key={id} className="absolute p-4 bg-sheet border-2 border-accent box-border flex gap-3.5 items-center" style={{ left: p.left, top: p.top, width: p.w, ...settle(p.delay) }}>
          {sail ? <SailBadge level={sail} size="md" /> : <SailPlaceholder size="md" label="CERT." />}
          <div><span className="t-micro-10 text-ink-low">SAIL</span><div className="mt-1.5 t-cap leading-[1.4] text-ink-mid">{n.rule}</div><div className="mt-2"><CitationChip reference={n.citation!} /></div></div>
        </div>
      );
    return (
      <button
        key={id}
        type="button"
        aria-expanded={isOpen}
        onClick={() => toggle(id)}
        className={cn("absolute text-left p-3.5 bg-sheet-raised border box-border tr-ui", isOpen ? "border-accent-line" : "border-hairline-strong hover:border-ink-low", band)}
        style={{ left: p.left, top: p.top, width: p.w, ...settle(p.delay) }}
      >
        <div className="flex items-baseline justify-between">
          <span className="t-micro text-ink-low">{n.term}</span>
          <span className="text-[22px] font-bold leading-none text-ink-hi tnum">{n.value}</span>
        </div>
        <div className="mt-2 t-cap leading-[1.4] text-ink-mid line-clamp-3">{n.rule}</div>
        {n.citation && <div className="mt-2"><CitationChip reference={n.citation} /></div>}
      </button>
    );
  };

  // Mobile: indented outline, root first, identical node anatomy.
  const outline: [string, number][] = [["root-sail", 0], ["n-grc", 1], ["n-igrc", 2], ["f-dim", 3], ["f-ground", 3], ["n-rarc", 1], ["n-arc", 2], ["f-alt", 3], ["f-airspace", 3], ["f-aerodrome", 3]];

  return (
    <div>
      <div className="flex items-baseline justify-between gap-4 mb-4 flex-wrap">
        <div>
          <h3 className="m-0 t-h3 text-ink-hi">Derivation</h3>
          <p className="mt-1 mb-0 t-body-sm text-ink-mid">Leaves are facts you confirmed. Every node names the rule that fired.</p>
        </div>
        <Button variant="ghost" onClick={onReplay} className="t-micro-10 px-3">Replay</Button>
      </div>

      <div className="hidden md:block">
        <div className="overflow-x-auto bg-sheet-well rounded-sm p-4">
          <div key={runKey} className="relative w-[960px] h-[520px]">
            <svg width="960" height="520" viewBox="0 0 960 520" fill="none" className="absolute inset-0" aria-hidden>
              {EDGES.map((e, i) => (
                <path key={i} d={e.d} stroke={e.accent ? "var(--accent)" : "var(--hairline-strong)"} strokeWidth={e.accent ? 2 : 1.5}
                  style={{ ["--edge-len" as string]: e.len, strokeDasharray: e.len, animation: `edge-draw ${e.dur ?? 520}ms var(--ease-instrument) ${e.delay}ms both` }} />
              ))}
            </svg>
            {Object.keys(POS).map(node)}
          </div>
        </div>
        <Inspector nodes={open.map((id) => byId.get(id)!).filter(Boolean)} byId={byId} onClose={toggle} />
      </div>

      <ol key={`o${runKey}`} className="md:hidden m-0 p-3 list-none bg-sheet-well rounded-sm flex flex-col gap-sheet">
        {outline.map(([id, depth], i) => {
          const n = byId.get(id)!;
          const isOpen = open.includes(id);
          const head = n.kind === "fact" ? "Fact" : `${n.term} ${n.value}${n.citation ? ` · ${n.citation.replace("SORA 2.5 · ", "")}` : ""}`;
          return (
            <li key={id} style={{ marginLeft: depth * 12, ...settle(i * 40) }} className={cn("bg-sheet", n.kind === "root" && "border-l-2 border-accent", changed.has(id) && "shadow-[inset_2px_0_0_var(--accent)]")}>
              {n.kind === "fact" ? (
                <div className="p-3"><span className="t-micro-10 text-ink-low">{head}</span><div className="mt-1.5 t-body-sm leading-[1.4] text-ink-mid">{n.rule}</div></div>
              ) : (
                <button type="button" aria-expanded={isOpen} onClick={() => toggle(id)} className="w-full text-left bg-transparent border-0 p-3 min-h-11">
                  <span className="flex items-center justify-between gap-2">
                    <span className="t-micro-10 text-ink-low">{head}</span>
                    <span aria-hidden className={cn("text-ink-low text-xs tr-ui", isOpen && "rotate-180")}>▾</span>
                  </span>
                  <span className={cn("block mt-1.5 text-ink-hi", n.kind === "root" ? "text-[15px] font-semibold leading-[1.3]" : "t-body-sm leading-[1.4] text-ink-mid")}>{n.kind === "root" ? `${n.value} — ${n.rule}` : n.rule}</span>
                  {isOpen && (
                    <span className="mt-2 flex flex-col gap-1">
                      {n.citation && <CitationChip reference={n.citation} />}
                      {n.detail?.map((l) => <span key={l} className="t-data-sm text-ink-low">{l}</span>)}
                    </span>
                  )}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
