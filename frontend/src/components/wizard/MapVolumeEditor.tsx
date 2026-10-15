"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useMemo, useRef, useState } from "react";
import { AERODROME, CELLS, GEO_ZONES, RIVER, ROAD, WORLD } from "@/data/map";
import { analyse, bandOf, bufferOutline, DENSITY_BANDS, nearestOnLine, toPath, type Pt, type Volumes } from "@/engine/geometry";
import { cn } from "@/lib/cn";

export type LayerKey = "fg" | "cv" | "grb" | "pop" | "zones";
export type Layers = Record<LayerKey, boolean>;

const LAYER_ROWS: { k: LayerKey; label: string; swatch: React.CSSProperties }[] = [
  { k: "fg", label: "Flight geography", swatch: { background: "var(--accent)" } },
  { k: "cv", label: "Contingency volume", swatch: { border: "2px dashed var(--accent-line)" } },
  { k: "grb", label: "Ground risk buffer", swatch: { border: "2px solid var(--sail-4)" } },
  { k: "pop", label: "Population density", swatch: { background: "repeating-linear-gradient(45deg,var(--text-low) 0 1px,transparent 1px 5px)" } },
  { k: "zones", label: "ED-269 geo-zones", swatch: { border: "2px solid var(--arc-c)" } },
];

const line = (pts: Pt[]) => "M" + pts.map((p) => `${p.x},${p.y}`).join("L");
const fmt = (n: number) => n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function useMapAnalysis(pts: Pt[], v: Volumes) {
  return useMemo(() => {
    const a = analyse(pts, v, CELLS);
    const rGrb = v.fgHalfWidth + v.cvMargin + v.grbMargin;
    const zones = GEO_ZONES.filter((z) => {
      // a zone counts when the ground risk buffer reaches it
      const corners = [{ x: z.x, y: z.y }, { x: z.x + z.w, y: z.y }, { x: z.x, y: z.y + z.h }, { x: z.x + z.w, y: z.y + z.h }];
      const inside = pts.some((p) => p.x >= z.x && p.x <= z.x + z.w && p.y >= z.y && p.y <= z.y + z.h);
      return inside || corners.some((c) => nearestOnLine(c, pts).dist <= rGrb) || edgeNear(z, pts, rGrb);
    });
    const ad = nearestOnLine(AERODROME, pts).dist / 1000;
    return { ...a, zones: zones.map((z) => z.id), aerodromeKm: Math.round(ad * 10) / 10 };
  }, [pts, v]);
}

function edgeNear(z: { x: number; y: number; w: number; h: number }, pts: Pt[], r: number) {
  for (const p of pts) {
    const dx = Math.max(z.x - p.x, 0, p.x - (z.x + z.w)), dy = Math.max(z.y - p.y, 0, p.y - (z.y + z.h));
    if (Math.hypot(dx, dy) <= r) return true;
  }
  for (let i = 1; i < pts.length; i++)
    for (let k = 0; k <= 40; k++) {
      const p = { x: pts[i - 1].x + ((pts[i].x - pts[i - 1].x) * k) / 40, y: pts[i - 1].y + ((pts[i].y - pts[i - 1].y) * k) / 40 };
      const dx = Math.max(z.x - p.x, 0, p.x - (z.x + z.w)), dy = Math.max(z.y - p.y, 0, p.y - (z.y + z.h));
      if (Math.hypot(dx, dy) <= r) return true;
    }
  return false;
}

/** The designed chart surface: graticule, terrain abstraction, then five toggleable layers. */
export function MapCanvas({ pts, onChange, v, layers, extrudeKey, onCommit, className }: {
  pts: Pt[]; onChange: (p: Pt[]) => void; v: Volumes; layers: Layers; extrudeKey: number; onCommit: () => void; className?: string;
}) {
  const svg = useRef<SVGSVGElement>(null);
  const [zoom, setZoom] = useState(1);
  const [center, setCenter] = useState({ x: WORLD.w / 2, y: WORLD.h / 2 });
  const drag = useRef<{ kind: "vertex"; i: number } | { kind: "pan"; x: number; y: number; c: Pt } | null>(null);
  const reduce = useReducedMotion();

  const vw = WORLD.w / zoom, vh = WORLD.h / zoom;
  const vb = { x: Math.min(Math.max(center.x - vw / 2, 0), WORLD.w - vw), y: Math.min(Math.max(center.y - vh / 2, 0), WORLD.h - vh) };

  const toWorld = (e: React.PointerEvent) => {
    const r = svg.current!.getBoundingClientRect();
    return { x: vb.x + ((e.clientX - r.left) / r.width) * vw, y: vb.y + ((e.clientY - r.top) / r.height) * vh };
  };
  const mPerPx = () => vw / (svg.current?.getBoundingClientRect().width || 900);

  const rFg = v.fgHalfWidth, rCv = rFg + v.cvMargin, rGrb = rCv + v.grbMargin;
  const outlines = useMemo(() => ({ fg: toPath(bufferOutline(pts, rFg, 16)), cv: toPath(bufferOutline(pts, rCv, 16)), grb: toPath(bufferOutline(pts, rGrb, 16)) }), [pts, rFg, rCv, rGrb]);

  const scaleM = zoom >= 4 ? 250 : zoom >= 2 ? 500 : 1000;
  const extrude = (i: number): React.CSSProperties => (reduce ? {} : { transformBox: "fill-box", transformOrigin: "center", animation: `volume-extrude var(--t-media) var(--ease-instrument) ${i * 120}ms both` });
  const adDir = { x: AERODROME.x, y: Math.min(AERODROME.y, vb.y + vh) };

  return (
    <div className={cn("relative bg-sheet-well rounded-md overflow-hidden select-none touch-none", className)}>
      <svg
        ref={svg}
        viewBox={`${vb.x} ${vb.y} ${vw} ${vh}`}
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 size-full"
        role="img"
        aria-label="Flight geography chart. Drag the corridor vertices to adjust the flight geography."
        onPointerDown={(e) => {
          if ((e.target as Element).getAttribute("data-vertex")) return;
          (e.currentTarget as Element).setPointerCapture(e.pointerId);
          drag.current = { kind: "pan", x: e.clientX, y: e.clientY, c: center };
        }}
        onPointerMove={(e) => {
          const d = drag.current;
          if (!d) return;
          if (d.kind === "vertex") {
            const w = toWorld(e);
            onChange(pts.map((p, i) => (i === d.i ? { x: Math.round(Math.min(Math.max(w.x, 0), WORLD.w)), y: Math.round(Math.min(Math.max(w.y, 0), WORLD.h)) } : p)));
          } else if (zoom > 1) {
            const k = mPerPx();
            setCenter({ x: d.c.x - (e.clientX - d.x) * k, y: d.c.y - (e.clientY - d.y) * k });
          }
        }}
        onPointerUp={() => { if (drag.current?.kind === "vertex") onCommit(); drag.current = null; }}
      >
        <defs>
          {DENSITY_BANDS.map((b, i) => b.spacing > 0 && (
            <pattern key={i} id={`hatch-${i}`} width={b.spacing * 18} height={b.spacing * 18} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2={b.spacing * 18} stroke="var(--text-low)" strokeWidth={i >= 3 ? 40 : 22} opacity={0.55} />
            </pattern>
          ))}
        </defs>
        {/* graticule, 1 km */}
        <g stroke="var(--hairline)" strokeWidth="1" vectorEffect="non-scaling-stroke">
          {Array.from({ length: WORLD.w / 1000 + 1 }, (_, i) => <line key={`v${i}`} x1={i * 1000} y1={0} x2={i * 1000} y2={WORLD.h} vectorEffect="non-scaling-stroke" />)}
          {Array.from({ length: WORLD.h / 1000 + 1 }, (_, i) => <line key={`h${i}`} x1={0} y1={i * 1000} x2={WORLD.w} y2={i * 1000} vectorEffect="non-scaling-stroke" />)}
        </g>
        {layers.pop && (
          <g aria-hidden>
            {CELLS.map((c, i) => { const b = bandOf(c.density); return b > 0 && <rect key={i} x={c.x} y={c.y} width={c.size} height={c.size} fill={`url(#hatch-${b})`} />; })}
          </g>
        )}
        <path d={line(RIVER)} stroke="var(--hairline-strong)" strokeWidth="2" fill="none" vectorEffect="non-scaling-stroke" />
        <path d={line(ROAD)} stroke="var(--hairline-strong)" strokeWidth="1" strokeDasharray="6 5" fill="none" vectorEffect="non-scaling-stroke" />
        {layers.zones && GEO_ZONES.map((z) => (
          <g key={z.id}>
            <rect x={z.x} y={z.y} width={z.w} height={z.h} fill="var(--arc-c)" fillOpacity={0.18} stroke="var(--arc-c)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
            <text x={z.x + 120} y={z.y + 360} fill="var(--text-hi)" fontSize={260 / zoom} fontWeight={600} letterSpacing={20 / zoom}>{z.id}</text>
          </g>
        ))}
        <g key={extrudeKey}>
          {layers.grb && <path d={outlines.grb} fill="none" stroke="var(--sail-4)" strokeWidth="2" opacity={0.9} vectorEffect="non-scaling-stroke" style={extrude(2)} />}
          {layers.cv && <path d={outlines.cv} fill="none" stroke="var(--accent-line)" strokeWidth="2" strokeDasharray="6 4" vectorEffect="non-scaling-stroke" style={extrude(1)} />}
          {layers.fg && <path d={outlines.fg} fill="var(--accent)" fillOpacity={0.28} stroke="var(--accent)" strokeWidth="2" vectorEffect="non-scaling-stroke" style={extrude(0)} />}
        </g>
        <path d={line(pts)} stroke="var(--text-hi)" strokeWidth="1" strokeDasharray="2 4" fill="none" vectorEffect="non-scaling-stroke" />
        {pts.map((p, i) => (
          <circle
            key={i} cx={p.x} cy={p.y} r={110 / zoom} data-vertex="1"
            fill="var(--sheet)" stroke="var(--accent)" strokeWidth="2" vectorEffect="non-scaling-stroke"
            className="cursor-grab"
            onPointerDown={(e) => { e.stopPropagation(); (e.currentTarget.ownerSVGElement as Element).setPointerCapture(e.pointerId); drag.current = { kind: "vertex", i }; }}
          />
        ))}
        {/* aerodrome, off-chart: chevron on the edge */}
        <g transform={`translate(${adDir.x} ${adDir.y - 260 / zoom})`}>
          <path d={`M${-140 / zoom},${-60 / zoom} L0,${80 / zoom} L${140 / zoom},${-60 / zoom}`} stroke="var(--arc-c)" strokeWidth="2" fill="none" vectorEffect="non-scaling-stroke" />
          <text x={200 / zoom} y={40 / zoom} fill="var(--text-mid)" fontSize={220 / zoom} fontWeight={600}>{AERODROME.icao}</text>
        </g>
      </svg>

      <div className="absolute left-3 bottom-3 flex items-center gap-2 bg-sheet px-2.5 py-2 rounded-sm pointer-events-none">
        <div className="h-[2px] bg-ink-hi" style={{ width: Math.round(scaleM / (vw / 900)) }} />
        <span className="t-data-sm text-[11px] leading-none text-ink-hi">{scaleM >= 1000 ? `${scaleM / 1000} km` : `${scaleM} m`}</span>
      </div>
      <div className="absolute left-3 top-3 bg-sheet px-2 py-1.5 rounded-sm t-micro-10 text-ink-mid pointer-events-none" aria-hidden>N ↑</div>
      <div className="absolute right-3 top-3 flex flex-col gap-sheet">
        <button type="button" aria-label="Zoom in" disabled={zoom >= 4} onClick={() => setZoom((z) => Math.min(4, z * 2))} className="size-11 bg-sheet border border-hairline text-ink-hi text-base disabled:opacity-35">+</button>
        <button type="button" aria-label="Zoom out" disabled={zoom <= 1} onClick={() => setZoom((z) => Math.max(1, z / 2))} className="size-11 bg-sheet border border-hairline text-ink-hi text-base disabled:opacity-35">−</button>
      </div>
    </div>
  );
}

export function LayerControl({ layers, onToggle }: { layers: Layers; onToggle: (k: LayerKey) => void }) {
  return (
    <div>
      <span className="t-micro text-ink-low">Layers</span>
      <div className="mt-2 flex flex-col">
        {LAYER_ROWS.map((l) => (
          <button key={l.k} type="button" aria-pressed={layers[l.k]} onClick={() => onToggle(l.k)}
            className={cn("flex items-center gap-2.5 w-full min-h-11 px-2.5 bg-transparent border-0 text-left text-[13px] font-medium leading-none tr-ui", layers[l.k] ? "text-ink-hi" : "text-ink-low")}>
            <span className="size-[18px] flex-none rounded-sm box-border" style={{ ...l.swatch, opacity: layers[l.k] ? 1 : 0.25 }} />
            <span className="flex-1">{l.label}</span>
            <span aria-hidden className="text-ink-low">{layers[l.k] ? "●" : "○"}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function DensityLegend({ peak }: { peak: number }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="t-micro text-ink-low">Density · ppl/km²</span>
      <div className="flex gap-sheet">
        {DENSITY_BANDS.map((b, i) => (
          <div key={b.label} className={cn("flex-1 flex flex-col gap-1", bandOf(peak) === i && "text-ink-hi")}>
            <span className="h-4 border border-hairline" style={{ background: b.spacing ? `repeating-linear-gradient(45deg,var(--text-low) 0 1px,transparent 1px ${b.spacing}px)` : "transparent" }} />
            <span className={cn("text-[10px] leading-none tnum", bandOf(peak) === i ? "text-ink-hi font-semibold" : "text-ink-low")}>{b.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AreaReadout({ a }: { a: ReturnType<typeof useMapAnalysis> }) {
  const rows: [string, string][] = [
    ["Flight geography", `${fmt(a.fg)} km²`],
    ["Contingency volume", `${fmt(a.cv)} km²`],
    ["Ground risk buffer", `${fmt(a.grb)} km²`],
    ["Peak density", `${a.peak.toLocaleString("en-GB")} ppl/km²`],
    ["Corridor length", `${a.lengthKm.toFixed(1)} km`],
  ];
  return (
    <div className="flex flex-col gap-2.5">
      <span className="t-micro text-ink-low">Area readout</span>
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 items-baseline t-data-13 text-ink-hi">
          <span className="text-ink-mid whitespace-nowrap">{k}</span><span className="whitespace-nowrap">{v}</span>
        </div>
      ))}
    </div>
  );
}

export function AdjacentWarning({ a }: { a: ReturnType<typeof useMapAnalysis> }) {
  if (!a.adjacent) return null;
  return (
    <div className="p-3 bg-sheet-well border-l-[3px] border-sail-3 rounded-sm">
      <span className="t-micro-10 text-sail-3">Adjacent area</span>
      <p className="mt-1.5 mb-0 t-cap text-ink-mid pretty">
        The ground risk buffer comes within {a.adjacent.distance} m of a populated cell ({a.adjacent.density.toLocaleString("en-GB")} ppl/km²) to the {a.adjacent.direction}. Containment will be assessed after the SAIL.
      </p>
    </div>
  );
}

/** Mobile: full-bleed chart with a draggable sheet at three detents (88 / half / full). */
export function MapSheet({ children, height }: { children: React.ReactNode; height: number }) {
  const detents = [height - 88, height / 2, 0];
  const [d, setD] = useState(0);
  const reduce = useReducedMotion();
  return (
    <motion.div
      className="absolute inset-x-0 bottom-0 bg-sheet rounded-t-md shadow-overlay flex flex-col"
      style={{ height }}
      drag="y"
      dragConstraints={{ top: 0, bottom: detents[0] }}
      dragElastic={0.04}
      animate={{ y: detents[d] }}
      transition={reduce ? { duration: 0 } : { duration: 0.24, ease: [0.22, 0.61, 0.36, 1] }}
      onDragEnd={(_, info) => {
        const y = detents[d] + info.offset.y;
        let best = 0;
        detents.forEach((t, i) => { if (Math.abs(t - y) < Math.abs(detents[best] - y)) best = i; });
        setD(best);
      }}
    >
      <button type="button" onClick={() => setD((x) => (x + 1) % 3)} aria-label={["Expand map panel", "Expand map panel fully", "Collapse map panel"][d]}
        className="w-full min-h-11 bg-transparent border-0 flex items-center justify-center cursor-grab">
        <span className="w-10 h-1 rounded-pill bg-hairline-strong" />
      </button>
      <div className="px-4 pb-4 flex flex-col gap-4 overflow-y-auto">{children}</div>
    </motion.div>
  );
}
