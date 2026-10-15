# SORA Copilot — MediaSlot manifest

Every slot reserves its aspect ratio in layout, so the real asset lands with no shift.
Placeholders use the house crop-mark frame; the slot id renders only in dev mode
(`dev` prop / `?slots=1`).

Static export: no image optimisation. Ship the exact intrinsic sizes below, plus a 2×
variant where noted. Hero video must stay under 2.5 MB to hold LCP < 2.5s on a cold
connection — H.264 MP4 with a WebM sibling, `muted autoplay loop playsinline preload="none"`,
and `poster` set to `hero-poster`.

| Slot id | Page | Type | Ratio | Intrinsic | What it should depict |
|---|---|---|---|---|---|
| `hero-loop` | Landing | video | 16:9 | 1440×810 (≤2.5 MB, 12 s loop) | Screen capture: an operational volume drawn on the map, contingency and buffer extruding, then the SAIL badge resolving. No cursor trails, no UI chrome outside the app frame. |
| `hero-poster` | Landing | image | 16:9 | 1440×810, 2× @2880 | First frame of `hero-loop`. Also the `prefers-reduced-motion` fallback. |
| `feature-trace` | Landing | image | 4:3 | 1280×960 | The derivation tree at full width, three nodes expanded, citations legible at 100%. |
| `feature-map` | Landing | image | 4:3 | 1280×960 | Map step with flight geography, contingency volume, ground risk buffer and the density overlay on. |
| `feature-dossier` | Landing | image | 3:4 | 900×1200 | A page of the exported DOCX: the OSO matrix with evidence references. Real typography, not a mock. |
| `feature-counterfactual` | Landing | video | 1:1 | 900×900 (≤1.2 MB, 6 s loop) | Altitude parameter changing, then SAIL stepping III → II one plate at a time. |
| `proof-logos` | Landing | image | 6:1 | 1200×200 | Authority and standards marks in one monochrome row. Reference only — the no-endorsement line sits beside it. |
| `persona-1` | Landing | image | 1:1 | 600×600, 2× @1200 | Two-person inspection team on a roof in Graz, mid-task, equipment visible. |
| `persona-2` | Landing | image | 1:1 | 600×600, 2× @1200 | Solo BVLOS operator at a ground controller in a field. Daylight, no gear-porn close-up. |
| `persona-3` | Landing | image | 1:1 | 600×600, 2× @1200 | Compliance officer reading a printed dossier at a desk. Paper, pen, no screen glow. |
| `dossier-preview` | Dossier builder | image | 3:4 | 900×1200 | Rendered page 14 of the generated DOCX, OSO matrix section. |
| `empty-operations` | App — operations | illustration | 1:1 | 480×480 SVG | Line schematic: an empty operational-volume outline over a blank graticule. Two ink weights, one accent mark. No characters, no 3D, no drone. |
| `empty-dossiers` | App — dossiers | illustration | 1:1 | 480×480 SVG | Line schematic: an unbound document stack with corner registration marks. Same two-weight language. |
| `empty-fleet` | App — fleet | illustration | 1:1 | 480×480 SVG | Line schematic: an empty aircraft record card, dimension callouts unfilled. |
| `og-default` | Meta | image | 1.91:1 | 1200×630 | Social card: black ground, wordmark, the chain iGRC → GRC → ARC → SAIL set as the only graphic. |

## Asset conventions

- **Photography** (personas): daylight, natural contrast, people working rather than posed.
  Code filter `saturate(.95) contrast(1.02)`. No duotone, no grain, no blur-behind-text.
- **Screen captures**: taken in dark theme at 2× on a 1440 frame, cropped to the stated
  ratio, no browser chrome, no OS cursor.
- **Illustrations**: SVG, stroke only, `currentColor` so they inherit the theme, two
  weights (1px structure, 2px subject), at most one `--accent` mark each.
- **Containment**: media is full-bleed in the hero and sheet-contained everywhere else,
  radius `--radius-md`, with crop marks on the frame rather than a border.
