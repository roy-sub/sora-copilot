/**
 * The single media registry (build spec §11).
 *
 * One entry per slot in `design/project/media-manifest.md`. `<MediaSlot id="hero-loop" />`
 * reads everything it needs from here — ratio, intrinsic size, what the asset depicts —
 * so when real files are dropped into `public/media/` with these filenames they simply
 * appear. No code change.
 *
 * `w`/`h` are the intrinsic dimensions from the design manifest and are what reserves the
 * aspect ratio, so the real asset lands with zero layout shift.
 */

export interface MediaEntry {
  kind: "image" | "video" | "illustration";
  src: string;
  /** Poster frame, and the `prefers-reduced-motion` fallback for a video. */
  poster?: string;
  w: number;
  h: number;
  alt: string;
  /** Shown in the placeholder: what this asset should depict. */
  note: string;
  /** Design-manifest size budget, shown in dev so an oversized asset is noticed. */
  maxBytes?: number;
}

export const MEDIA = {
  "hero-loop": {
    kind: "video",
    src: "/media/hero-loop.mp4",
    poster: "/media/hero-poster.jpg",
    w: 1440,
    h: 810,
    alt: "An operational volume being drawn on the map, then the SAIL badge resolving",
    note: "Screen capture: an operational volume drawn on the map, contingency and buffer extruding, then the SAIL badge resolving. 12 s loop, no cursor trails.",
    maxBytes: 2_500_000,
  },
  "hero-poster": {
    kind: "image",
    src: "/media/hero-poster.jpg",
    w: 1440,
    h: 810,
    alt: "The map and SAIL badge at rest",
    note: "First frame of hero-loop. Also the reduced-motion fallback. 2× variant at 2880 wide.",
  },
  "feature-trace": {
    kind: "image",
    src: "/media/feature-trace.png",
    w: 1280,
    h: 960,
    alt: "The derivation tree with three nodes expanded, each showing its citation",
    note: "The derivation tree at full width, three nodes expanded, citations legible at 100%.",
  },
  "feature-map": {
    kind: "image",
    src: "/media/feature-map.png",
    w: 1280,
    h: 960,
    alt: "Flight geography, contingency volume and ground risk buffer on the chart",
    note: "Map step with flight geography, contingency volume, ground risk buffer and the density overlay on.",
  },
  "feature-dossier": {
    kind: "image",
    src: "/media/feature-dossier.png",
    w: 900,
    h: 1200,
    alt: "A page of the exported dossier showing the OSO matrix",
    note: "The OSO matrix page of the real generated PDF, rasterised at 160 dpi. Real typography, not a mock — a mock of your own output is the one illustration nobody needs.",
  },
  "feature-counterfactual": {
    kind: "video",
    src: "/media/feature-counterfactual.mp4",
    poster: "/media/feature-counterfactual.jpg",
    w: 900,
    h: 900,
    alt: "An altitude change stepping SAIL from III to II",
    note: "Altitude parameter changing, then SAIL stepping III → II one plate at a time. 6 s loop.",
    maxBytes: 1_200_000,
  },
  "proof-logos": {
    kind: "image",
    src: "/media/proof-logos.png",
    w: 1200,
    h: 200,
    alt: "The frameworks the engine implements, as a monochrome row of regulation names",
    note: "The regulations themselves, set as type — never a reproduction of an authority's logo, which would read as endorsement next to a line saying none is implied.",
  },
  "persona-1": {
    kind: "image",
    src: "/media/persona-1.jpg",
    w: 600,
    h: 600,
    alt: "The intake a roof survey produces: VLOS at 42 m, sparsely populated, 84 ppl/km², a 2.3 m aircraft",
    note: "Segment card, not a photograph: the facts this segment types in. A photograph of a customer who does not exist is a fabricated endorsement, and the copy beside it describes a segment rather than quoting a person.",
  },
  "persona-2": {
    kind: "image",
    src: "/media/persona-2.jpg",
    w: 600,
    h: 600,
    alt: "The intake a corridor operation produces: BVLOS at 118 m, a 12.4 km corridor, class G near an aerodrome",
    note: "Segment card, not a photograph. Inputs only — nothing on it is a class the engine computed.",
  },
  "persona-3": {
    kind: "image",
    src: "/media/persona-3.jpg",
    w: 600,
    h: 600,
    alt: "A trace excerpt: conclusion sail(III), rule sora25.sail.lookup, premises grc(4) and arc_residual(b), source Table 7",
    note: "Segment card, not a photograph: the justification this reader opens before the verdict, in the shape the product actually emits it.",
  },
  "dossier-preview": {
    kind: "image",
    src: "/media/dossier-preview.png",
    w: 900,
    h: 1200,
    alt: "A page of the generated dossier showing the derivation appendix",
    note: "The derivation appendix of the real generated PDF, rasterised — a different page from feature-dossier, so the two slots are not the same picture twice.",
  },
  "empty-operations": {
    kind: "illustration",
    src: "/media/empty-operations.svg",
    w: 480,
    h: 480,
    alt: "An empty operational-volume outline over a blank graticule",
    note: "Line schematic: an empty operational-volume outline over a blank graticule. Two ink weights, one accent mark.",
  },
  "empty-dossiers": {
    kind: "illustration",
    src: "/media/empty-dossiers.svg",
    w: 480,
    h: 480,
    alt: "An unbound document stack with corner registration marks",
    note: "Line schematic: an unbound document stack with corner registration marks. Two weights.",
  },
  "empty-fleet": {
    kind: "illustration",
    src: "/media/empty-fleet.svg",
    w: 480,
    h: 480,
    alt: "An empty aircraft record card with unfilled dimension callouts",
    note: "Line schematic: an empty aircraft record card, dimension callouts unfilled.",
  },
  "og-default": {
    kind: "image",
    src: "/media/og-default.png",
    w: 1200,
    h: 630,
    alt: "SORA Copilot — from mission to dossier in minutes",
    note: "Social card: black ground, wordmark, the chain iGRC → GRC → ARC → SAIL as the only graphic.",
  },
} as const satisfies Record<string, MediaEntry>;

export type MediaId = keyof typeof MEDIA;

export const mediaEntry = (id: MediaId): MediaEntry => MEDIA[id];

/** "16 / 9" for the CSS aspect-ratio, straight from the intrinsic size. */
export const mediaRatio = (id: MediaId): string => `${MEDIA[id].w} / ${MEDIA[id].h}`;

/** "1440×810", as the design manifest writes it. */
export const mediaSize = (id: MediaId): string => `${MEDIA[id].w}×${MEDIA[id].h}`;
