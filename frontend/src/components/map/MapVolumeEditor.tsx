"use client";

/**
 * The map step: MapLibre GL, with the designed chart layers drawn over it.
 *
 * Per the build spec this is MapLibre rather than the design phase's in-page SVG. The
 * design's layer stack is preserved as MapLibre style layers — flight geography in the
 * accent, contingency volume as a dashed accent outline, ground risk buffer in sail-4,
 * the adjacent area as a hairline ring — so what changed is the surface underneath, not
 * the instrument on top.
 *
 * Two things are deliberate:
 *
 * - **The basemap is optional.** With no `NEXT_PUBLIC_MAP_STYLE_URL` the map renders on
 *   the designed graticule with no network at all, which keeps the step usable offline
 *   and in a printed dossier. A style URL adds a basemap beneath the same layers.
 * - **The server owns the volumes.** Dragging shows a local approximation so the readout
 *   does not freeze; on release the flight geography is saved and `POST /geo/derive`
 *   returns the real volumes, computed in an equal-area projection.
 */

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { GeoJSONPolygon } from "@/lib/api-client";
import { env } from "@/lib/env";
import {
  areaKm2,
  bounds,
  centroid,
  defaultRing,
  fromPolygon,
  perimeterM,
  selfIntersects,
  toPolygon,
  type LngLat,
} from "@/lib/geo";
import { cn } from "@/lib/cn";

export type LayerKey = "fg" | "cv" | "grb" | "adjacent" | "basemap";
export type Layers = Record<LayerKey, boolean>;

export const DEFAULT_LAYERS: Layers = { fg: true, cv: true, grb: true, adjacent: false, basemap: true };

export const LAYER_ROWS: { k: LayerKey; label: string; swatch: React.CSSProperties }[] = [
  { k: "fg", label: "Flight geography", swatch: { background: "var(--accent)" } },
  { k: "cv", label: "Contingency volume", swatch: { border: "2px dashed var(--accent-line)" } },
  { k: "grb", label: "Ground risk buffer", swatch: { border: "2px solid var(--sail-4)" } },
  { k: "adjacent", label: "Adjacent area", swatch: { border: "2px solid var(--hairline-strong)" } },
  { k: "basemap", label: "Basemap", swatch: { background: "var(--sheet-alt)" } },
];

export interface DerivedOutlines {
  contingency_volume?: GeoJSONPolygon | null;
  ground_risk_buffer?: GeoJSONPolygon | null;
  adjacent_area?: GeoJSONPolygon | null;
}

interface Props {
  /** The drawn outline, as a GeoJSON polygon. Null until the operator draws one. */
  value: GeoJSONPolygon | null;
  onChange: (polygon: GeoJSONPolygon) => void;
  /** Called when a drag finishes, so the caller can save and re-derive. */
  onCommit?: (polygon: GeoJSONPolygon) => void;
  derived?: DerivedOutlines;
  layers?: Layers;
  className?: string;
  /** Bumped by the caller to replay the extrude animation. */
  extrudeKey?: number;
}

type MapLibre = typeof import("maplibre-gl");

const EMPTY: GeoJSONPolygon = { type: "Polygon", coordinates: [[]] };

function featureCollection(polygon: GeoJSONPolygon | null) {
  return {
    type: "FeatureCollection" as const,
    features: polygon ? [{ type: "Feature" as const, properties: {}, geometry: polygon }] : [],
  };
}

function vertexCollection(ring: LngLat[]) {
  return {
    type: "FeatureCollection" as const,
    features: ring.map((p, i) => ({
      type: "Feature" as const,
      properties: { index: i },
      geometry: { type: "Point" as const, coordinates: [p.lng, p.lat] },
    })),
  };
}

/** Served from public/, copied there by prebuild. See setWorkerUrl below. */
const WORKER_URL = "/maplibre-gl-worker.mjs";

export function MapVolumeEditor({
  value,
  onChange,
  onCommit,
  derived,
  layers = DEFAULT_LAYERS,
  className,
  extrudeKey = 0,
}: Props) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<import("maplibre-gl").Map | null>(null);
  const gl = useRef<MapLibre | null>(null);
  const dragging = useRef<number | null>(null);
  const ringRef = useRef<LngLat[]>([]);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const labelId = useId();

  const ring = useMemo(() => fromPolygon(value), [value]);
  ringRef.current = ring;

  const invalid = ring.length >= 4 && selfIntersects(ring);

  // ---------------------------------------------------------------- create the map

  useEffect(() => {
    let cancelled = false;
    const node = container.current;
    if (!node) return;

    (async () => {
      try {
        const maplibre = await import("maplibre-gl");
        if (cancelled) return;
        gl.current = maplibre;

        // MapLibre 6 loads its worker from `new URL("./maplibre-gl-worker.mjs", base)`,
        // where the base comes from `import.meta.url`. Webpack cannot analyse that, so
        // it emits no worker chunk and the URL resolves to a file the export does not
        // contain: the worker fails, no tile is ever parsed, and the map draws nothing
        // but the graticule — in production as well as here. The file is copied into
        // public/ by `npm run prebuild` and pointed at explicitly.
        maplibre.setWorkerUrl(WORKER_URL);

        const centre = ring.length ? centroid(ring) : { lng: 15.44, lat: 47.12 };
        const instance = new maplibre.Map({
          container: node,
          // An empty style when no basemap is configured: the designed graticule and the
          // volume layers are added below, so the step works with no network.
          //
          // `glyphs` is OMITTED, not set to undefined. An object literal with
          // `glyphs: undefined` still has the key, MapLibre's style validator sees a
          // present-but-undefined value and rejects the style with "glyphs: string
          // expected, undefined found" — and a rejected style never fires `load`, so
          // `ready` stays false, the volume layers are never added and the fit never
          // runs. The step then showed the designed graticule and nothing on it, which
          // is exactly the documented no-basemap path silently not working.
          style: env.mapStyleUrl
            ? env.mapStyleUrl
            : { version: 8, sources: {}, layers: [] },
          center: [centre.lng, centre.lat],
          zoom: 12,
          attributionControl: env.mapStyleUrl ? { compact: true } : false,
          // The chart reads as an instrument, not a 3D scene.
          pitchWithRotate: false,
          dragRotate: false,
          maxPitch: 0,
        });
        map.current = instance;

        instance.on("error", (e) => {
          // A failed basemap must not take the step down: the volumes are the point.
          if (env.mapStyleUrl) setHint("The basemap could not be loaded. The volumes are unaffected.");
          console.warn("map error", e?.error ?? e);
        });

        instance.addControl(new maplibre.NavigationControl({ showCompass: false }), "top-right");
        instance.addControl(new maplibre.ScaleControl({ unit: "metric" }), "bottom-left");

        instance.on("load", () => {
          if (cancelled) return;
          addLayers(instance, maplibre);
          setReady(true);
        });
      } catch (err) {
        if (!cancelled) setFailed(err instanceof Error ? err.message : "The map could not start.");
      }
    })();

    return () => {
      cancelled = true;
      map.current?.remove();
      map.current = null;
    };
    // Created once; every later change flows through the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------- layers

  const addLayers = useCallback((instance: import("maplibre-gl").Map, maplibre: MapLibre) => {
    const ink = (name: string) =>
      getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#CAFF01";

    const accent = ink("--accent");
    const accentLine = ink("--accent-line") || accent;
    const sail4 = ink("--sail-4");
    const hairline = ink("--hairline-strong");

    for (const id of ["adjacent", "grb", "cv", "fg"] as const) {
      instance.addSource(id, { type: "geojson", data: featureCollection(null) });
    }
    instance.addSource("vertices", { type: "geojson", data: vertexCollection([]) });

    instance.addLayer({
      id: "adjacent-line",
      type: "line",
      source: "adjacent",
      paint: { "line-color": hairline, "line-width": 1, "line-dasharray": [2, 3] },
    });
    instance.addLayer({
      id: "grb-line",
      type: "line",
      source: "grb",
      paint: { "line-color": sail4, "line-width": 2 },
    });
    instance.addLayer({
      id: "cv-line",
      type: "line",
      source: "cv",
      paint: { "line-color": accentLine, "line-width": 2, "line-dasharray": [3, 2] },
    });
    instance.addLayer({
      id: "fg-fill",
      type: "fill",
      source: "fg",
      paint: { "fill-color": accent, "fill-opacity": 0.26 },
    });
    instance.addLayer({
      id: "fg-line",
      type: "line",
      source: "fg",
      paint: { "line-color": accent, "line-width": 2 },
    });
    // 44px target: the visible dot is 7px with a transparent 22px halo for the pointer.
    instance.addLayer({
      id: "vertex-halo",
      type: "circle",
      source: "vertices",
      paint: { "circle-radius": 14, "circle-color": accent, "circle-opacity": 0.001 },
    });
    instance.addLayer({
      id: "vertex-dot",
      type: "circle",
      source: "vertices",
      paint: {
        "circle-radius": 6,
        "circle-color": ink("--sheet") || "#121517",
        "circle-stroke-color": accent,
        "circle-stroke-width": 2,
      },
    });

    const canvas = instance.getCanvas();

    instance.on("mouseenter", "vertex-halo", () => {
      canvas.style.cursor = "grab";
    });
    instance.on("mouseleave", "vertex-halo", () => {
      if (dragging.current === null) canvas.style.cursor = "";
    });

    const startDrag = (e: import("maplibre-gl").MapLayerMouseEvent | import("maplibre-gl").MapLayerTouchEvent) => {
      const index = e.features?.[0]?.properties?.index;
      if (typeof index !== "number") return;
      e.preventDefault();
      dragging.current = index;
      canvas.style.cursor = "grabbing";
      instance.dragPan.disable();
    };
    instance.on("mousedown", "vertex-halo", startDrag);
    instance.on("touchstart", "vertex-halo", startDrag);

    const move = (e: import("maplibre-gl").MapMouseEvent | import("maplibre-gl").MapTouchEvent) => {
      const index = dragging.current;
      if (index === null) return;
      const next = ringRef.current.map((p, i) =>
        i === index ? { lng: e.lngLat.lng, lat: e.lngLat.lat } : p,
      );
      ringRef.current = next;
      const polygon = toPolygon(next);
      if (polygon) {
        (instance.getSource("fg") as import("maplibre-gl").GeoJSONSource | undefined)?.setData(
          featureCollection(polygon),
        );
        (instance.getSource("vertices") as import("maplibre-gl").GeoJSONSource | undefined)?.setData(
          vertexCollection(next),
        );
        onChange(polygon);
      }
    };
    instance.on("mousemove", move);
    instance.on("touchmove", move);

    const end = () => {
      if (dragging.current === null) return;
      dragging.current = null;
      canvas.style.cursor = "";
      instance.dragPan.enable();
      const polygon = toPolygon(ringRef.current);
      if (polygon) onCommit?.(polygon);
    };
    instance.on("mouseup", end);
    instance.on("touchend", end);

    void maplibre;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------- data updates

  useEffect(() => {
    const instance = map.current;
    if (!instance || !ready) return;
    const set = (id: string, polygon: GeoJSONPolygon | null | undefined) =>
      (instance.getSource(id) as import("maplibre-gl").GeoJSONSource | undefined)?.setData(
        featureCollection(polygon ?? null),
      );
    set("fg", value);
    set("cv", derived?.contingency_volume);
    set("grb", derived?.ground_risk_buffer);
    set("adjacent", derived?.adjacent_area);
    (instance.getSource("vertices") as import("maplibre-gl").GeoJSONSource | undefined)?.setData(
      vertexCollection(ring),
    );
  }, [ready, value, derived, ring, extrudeKey]);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !ready) return;
    const visible = (id: string, on: boolean) =>
      instance.getLayer(id) && instance.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    visible("fg-fill", layers.fg);
    visible("fg-line", layers.fg);
    visible("cv-line", layers.cv);
    visible("grb-line", layers.grb);
    visible("adjacent-line", layers.adjacent);
    for (const layer of instance.getStyle().layers ?? []) {
      // Basemap layers are everything the style brought that is not ours.
      if (!layer.id.match(/^(fg|cv|grb|adjacent|vertex)-/)) {
        instance.setLayoutProperty(layer.id, "visibility", layers.basemap ? "visible" : "none");
      }
    }
  }, [ready, layers]);

  // Fit to the outline once it exists, so the operator is never looking at empty ocean.
  const fitted = useRef(false);
  useEffect(() => {
    const instance = map.current;
    if (!instance || !ready || fitted.current || ring.length < 3) return;
    const box = bounds(ring);
    if (!box) return;
    instance.fitBounds(box, { padding: 72, duration: 0, maxZoom: 15 });
    fitted.current = true;
  }, [ready, ring]);

  // ---------------------------------------------------------------- drawing

  const draw = () => {
    const instance = map.current;
    const centre = instance
      ? { lng: instance.getCenter().lng, lat: instance.getCenter().lat }
      : undefined;
    const polygon = toPolygon(defaultRing(centre));
    if (polygon) {
      onChange(polygon);
      onCommit?.(polygon);
    }
  };

  const addVertex = () => {
    if (ring.length < 3) return;
    // Insert at the midpoint of the longest edge, which is where an operator wants more
    // control rather than wherever they happened to click.
    let longest = 0;
    let at = 0;
    for (let i = 0; i < ring.length; i++) {
      const a = ring[i];
      const b = ring[(i + 1) % ring.length];
      const d = Math.hypot(b.lng - a.lng, b.lat - a.lat);
      if (d > longest) {
        longest = d;
        at = i;
      }
    }
    const a = ring[at];
    const b = ring[(at + 1) % ring.length];
    const next = [...ring];
    next.splice(at + 1, 0, { lng: (a.lng + b.lng) / 2, lat: (a.lat + b.lat) / 2 });
    const polygon = toPolygon(next);
    if (polygon) {
      onChange(polygon);
      onCommit?.(polygon);
    }
  };

  const removeVertex = () => {
    if (ring.length <= 3) return;
    const polygon = toPolygon(ring.slice(0, -1));
    if (polygon) {
      onChange(polygon);
      onCommit?.(polygon);
    }
  };

  const localArea = ring.length >= 3 ? areaKm2(ring) : 0;

  return (
    // data-media is the capture hook for scripts/make-media.mjs. Selecting this panel by
    // shape instead ("the first svg") picked up a loading skeleton and shipped it.
    <div
      data-media="map"
      className={cn("relative bg-sheet-well rounded-md overflow-hidden", className)}
    >
      <div
        ref={container}
        className="absolute inset-0"
        role="application"
        aria-labelledby={labelId}
      />
      <span id={labelId} className="sr-only">
        Flight geography chart. Drag a vertex to adjust the outline; the contingency
        volume and ground risk buffer are derived from it.
      </span>

      {/* The designed graticule, under the volumes and over any basemap-less canvas. */}
      {!env.mapStyleUrl && (
        <div
          aria-hidden
          className="absolute inset-0 pointer-events-none opacity-60"
          style={{
            backgroundImage:
              "linear-gradient(var(--hairline) 1px,transparent 1px),linear-gradient(90deg,var(--hairline) 1px,transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
      )}

      {failed && (
        <div className="absolute inset-0 grid place-items-center p-6 bg-sheet-well">
          <div className="max-w-[40ch] flex flex-col gap-2 text-center">
            <span className="t-micro text-sail-6">Map unavailable</span>
            <p className="m-0 t-body-sm text-ink-mid pretty">{failed}</p>
            <p className="m-0 t-cap text-ink-low pretty">
              You can still enter the altitude and the ground environment; the volumes are
              derived on the server from the outline you save.
            </p>
          </div>
        </div>
      )}

      {!failed && ring.length < 3 && (
        <div className="absolute inset-0 grid place-items-center p-6">
          <div className="flex flex-col items-center gap-3 text-center max-w-[36ch] bg-sheet/90 p-5 rounded-md">
            <span className="t-micro text-ink-low">No flight geography</span>
            <p className="m-0 t-body-sm text-ink-mid pretty">
              Draw the area the aircraft will fly within. The contingency volume and
              ground risk buffer are derived from it — you do not enter them.
            </p>
            <button
              type="button"
              onClick={draw}
              className="min-h-11 px-4 bg-accent text-accent-ink rounded-sm t-micro-10 press tr-ui"
            >
              Start an outline here
            </button>
          </div>
        </div>
      )}

      {ring.length >= 3 && (
        <div className="absolute left-3 top-3 flex flex-col gap-sheet">
          <div className="bg-sheet px-2.5 py-2 rounded-sm flex flex-col gap-1 pointer-events-none">
            <span className="t-micro-10 text-ink-low">Drawn outline</span>
            <span className="t-data-13 text-ink-hi tnum">
              {localArea.toLocaleString("en-GB", { maximumFractionDigits: 2 })} km²
            </span>
            <span className="t-data-sm text-ink-low tnum">
              {ring.length} vertices · {(perimeterM(ring) / 1000).toFixed(1)} km around
            </span>
          </div>
          <div className="flex gap-sheet">
            <button
              type="button"
              onClick={addVertex}
              className="min-h-11 px-3 bg-sheet border border-hairline rounded-sm t-micro-10 text-ink-mid hover:text-ink-hi tr-ui"
            >
              Add vertex
            </button>
            <button
              type="button"
              onClick={removeVertex}
              disabled={ring.length <= 3}
              className="min-h-11 px-3 bg-sheet border border-hairline rounded-sm t-micro-10 text-ink-mid hover:text-ink-hi disabled:opacity-35 tr-ui"
            >
              Remove
            </button>
            <button
              type="button"
              onClick={draw}
              className="min-h-11 px-3 bg-sheet border border-hairline rounded-sm t-micro-10 text-ink-mid hover:text-ink-hi tr-ui"
            >
              Reset
            </button>
          </div>
        </div>
      )}

      {invalid && (
        <div
          role="alert"
          className="absolute left-3 right-3 bottom-14 bg-sheet border-l-[3px] border-sail-6 p-3 rounded-sm"
        >
          <span className="t-micro-10 text-sail-6">Outline crosses itself</span>
          <p className="m-0 mt-1 t-cap text-ink-mid pretty">
            The volumes cannot be derived from a self-intersecting outline. Drag the
            vertices apart, or reset and draw it again.
          </p>
        </div>
      )}

      {hint && !invalid && (
        <div className="absolute left-3 right-3 bottom-14 bg-sheet border-l-[3px] border-sail-3 p-2.5 rounded-sm">
          <p className="m-0 t-cap text-ink-mid pretty">{hint}</p>
        </div>
      )}
    </div>
  );
}

export { EMPTY as EMPTY_POLYGON };
