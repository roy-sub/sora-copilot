"use client";

/**
 * The map step's side panel: layers, the area readout, the density legend and the
 * adjacent-area advisory.
 *
 * Every number here comes from the server's derivation, which carries the rule that
 * produced it. The rules are shown, not hidden behind a tooltip: the map step is half
 * the product's credibility, and a buffer nobody can explain is worth nothing.
 */

import { LAYER_ROWS, type LayerKey, type Layers } from "@/components/map/MapVolumeEditor";
import type { GeoDerive } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import { fmtKm2, fmtM } from "@/lib/geo";

export function LayerControl({
  layers,
  onToggle,
  hasBasemap,
}: {
  layers: Layers;
  onToggle: (k: LayerKey) => void;
  hasBasemap: boolean;
}) {
  const rows = hasBasemap ? LAYER_ROWS : LAYER_ROWS.filter((r) => r.k !== "basemap");
  return (
    <div>
      <span className="t-micro text-ink-low">Layers</span>
      <div className="mt-2 flex flex-col">
        {rows.map((l) => (
          <button
            key={l.k}
            type="button"
            aria-pressed={layers[l.k]}
            onClick={() => onToggle(l.k)}
            className={cn(
              "flex items-center gap-2.5 w-full min-h-11 px-2.5 bg-transparent border-0 text-left text-[13px] font-medium leading-none tr-ui",
              layers[l.k] ? "text-ink-hi" : "text-ink-low",
            )}
          >
            <span
              className="size-[18px] flex-none rounded-sm box-border"
              style={{ ...l.swatch, opacity: layers[l.k] ? 1 : 0.25 }}
            />
            <span className="flex-1">{l.label}</span>
            <span aria-hidden className="text-ink-low">
              {layers[l.k] ? "●" : "○"}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function AreaReadout({ derived }: { derived: GeoDerive | null }) {
  const rows: [string, string][] = derived
    ? [
        ["Flight geography", `${fmtKm2(derived.flight_geography_km2)} km²`],
        ["Contingency volume", `${fmtKm2(derived.contingency_volume_km2)} km²`],
        ["Ground risk buffer", `${fmtKm2(derived.ground_risk_buffer_km2)} km²`],
        ["Adjacent area", `${fmtKm2(derived.adjacent_area_km2)} km²`],
      ]
    : [];

  return (
    <div className="flex flex-col gap-2.5">
      <span className="t-micro text-ink-low">Area readout</span>
      {derived ? (
        <>
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 items-baseline t-data-13 text-ink-hi">
              <span className="text-ink-mid whitespace-nowrap">{k}</span>
              <span className="whitespace-nowrap tnum">{v}</span>
            </div>
          ))}
          <div className="pt-2.5 mt-1 border-t border-hairline flex flex-col gap-1.5">
            <span className="t-micro-10 text-ink-low">Derived margins</span>
            <div className="flex justify-between gap-3 t-data-sm text-ink-mid">
              <span>Contingency, lateral</span>
              <span className="text-ink-hi tnum">{fmtM(derived.contingency_lateral_m)} m</span>
            </div>
            <div className="flex justify-between gap-3 t-data-sm text-ink-mid">
              <span>Contingency, vertical</span>
              <span className="text-ink-hi tnum">{fmtM(derived.contingency_vertical_m)} m</span>
            </div>
            <div className="flex justify-between gap-3 t-data-sm text-ink-mid">
              <span>Ground risk buffer</span>
              <span className="text-ink-hi tnum">{fmtM(derived.ground_risk_buffer_m)} m</span>
            </div>
          </div>
        </>
      ) : (
        <p className="m-0 t-cap text-ink-low pretty">
          Save an outline and the volumes are derived on the server, in an equal-area
          projection.
        </p>
      )}
    </div>
  );
}

/** Each derived number, with the rule that produced it. Expanded, not hidden. */
export function DerivationNotes({ derived }: { derived: GeoDerive | null }) {
  if (!derived?.derivations?.length) return null;
  return (
    <div className="flex flex-col gap-2">
      <span className="t-micro text-ink-low">How these were derived</span>
      {derived.derivations.map((d, i) => (
        <div key={i} className="p-2.5 bg-sheet-well rounded-sm flex flex-col gap-1">
          <span className="t-data-sm text-ink-hi tnum">{fmtM(Number(d.value_m))} m</span>
          <p className="m-0 t-cap leading-[1.45] text-ink-mid pretty">{String(d.rule)}</p>
        </div>
      ))}
      {derived.unverified && (
        <p className="m-0 t-cap text-sail-3 pretty">
          The buffer parameters are transcribed from a seed, not from the official text.
        </p>
      )}
    </div>
  );
}

const BANDS: { label: string; max: number | null; spacing: number }[] = [
  { label: "< 5", max: 5, spacing: 0 },
  { label: "5–50", max: 50, spacing: 14 },
  { label: "50–500", max: 500, spacing: 9 },
  { label: "500–5,000", max: 5000, spacing: 6 },
  { label: "> 5,000", max: null, spacing: 4 },
];

export function DensityLegend({ peak }: { peak: number | null }) {
  const active =
    peak === null ? -1 : BANDS.findIndex((b) => b.max === null || peak < b.max);
  return (
    <div className="flex flex-col gap-2">
      <span className="t-micro text-ink-low">Density · ppl/km²</span>
      <div className="flex gap-sheet">
        {BANDS.map((b, i) => (
          <div key={b.label} className="flex-1 flex flex-col gap-1">
            <span
              className="h-4 border border-hairline"
              style={{
                background: b.spacing
                  ? `repeating-linear-gradient(45deg,var(--text-low) 0 1px,transparent 1px ${b.spacing}px)`
                  : "transparent",
              }}
            />
            <span
              className={cn(
                "text-[10px] leading-none tnum",
                active === i ? "text-ink-hi font-semibold" : "text-ink-low",
              )}
            >
              {b.label}
            </span>
          </div>
        ))}
      </div>
      {peak === null && (
        <p className="m-0 t-cap text-ink-low">No density recorded yet. Enter one at the next step.</p>
      )}
    </div>
  );
}

export function AdjacentWarning({
  derived,
  populated,
}: {
  derived: GeoDerive | null;
  populated: boolean;
}) {
  if (!derived) return null;
  const ring = derived.adjacent_area_km2 - derived.ground_risk_buffer_km2;
  return (
    <div
      className={cn(
        "p-3 bg-sheet-well rounded-sm border-l-[3px]",
        populated ? "border-sail-3" : "border-hairline-strong",
      )}
    >
      <span className={cn("t-micro-10", populated ? "text-sail-3" : "text-ink-low")}>
        Adjacent area
      </span>
      <p className="mt-1.5 mb-0 t-cap text-ink-mid pretty">
        A {fmtM(derived.adjacent_area_m)} m ring outside the ground risk buffer, adding{" "}
        {fmtKm2(ring)} km².{" "}
        {populated
          ? "You marked it as populated, which the containment step takes into account."
          : "Not marked as populated. If people live or gather there, say so at the ground step."}
      </p>
    </div>
  );
}
