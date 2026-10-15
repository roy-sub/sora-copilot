# SORA Copilot — Design Plan (Pass 1, revised)

Revision note: you chose **full Dronex inheritance**, **a designed vector chart surface**
for the map, and **all screens in one delivery**. §0–§2 below are rewritten accordingly;
§9 records exactly what moved and what it cost.

---

## 0. Inheritance: Dronex, in full

The brand base is taken whole — black ground, paper sheets, concrete grey, acid lime,
Archivo + Outfit, zero/10/pill radii, no shadows, crop marks on media, 2px sheet gaps,
restrained value-shift motion. Where the brief's §4 and Dronex disagree, **Dronex wins**
and I note the tension rather than quietly splitting the difference.

Three things Dronex does not define and the product cannot ship without. These are
declared extensions, not reinterpretations:

1. **A graphite sheet ramp.** Dronex has one sheet colour (paper). An instrument panel
   needs at least four ink levels. Added as `--graphite-900…400`, built so that dark
   theme is Dronex's own structure with the sheet value inverted.
2. **The SAIL ramp.** Six risk steps. Dronex has one accent and no semantic colour.
3. **An ARC band.** Air risk is a different axis from ground risk; reusing the SAIL ramp
   for it would be a lie.

**The theme model, and it is the best thing to come out of the inheritance:** the page
ground is black in *both* themes. Only the sheets flip — graphite in dark, paper in light.
So the light theme is not a derived inversion, it is literally Dronex as shipped, and the
dark theme is the same construction with a different sheet stock. The hairline gaps, the
crop marks and the lime read identically in both.

**Unresolved tension, stated:** the brief forbids "near-black plus one acid accent". Full
inheritance is exactly that. What keeps it from being the generic version is that the
acid accent is never decorative here — lime marks the single primary action per view and
the focus ring, nothing else — and the darkness is four structural ink levels with
ground-through gaps rather than one background colour. If this still reads as the thing
you wanted to avoid when you see it, the escape hatch is a two-line change: swap
`--accent` to a cold cyan and the system holds.

---

## 1. Palette

### 1.1 Brand base — inherited, theme-invariant

| Token | Hex | Role |
|---|---|---|
| `--black` | `#000000` | The ground. Never a sheet. Shows through every 2px gap as a hairline rule. |
| `--paper` | `#F5F5F5` | Light-theme sheet. The default surface in light. |
| `--concrete` | `#D9D9D9` | Light-theme well — recessed areas, table bodies, fields at rest. |
| `--lime` | `#CAFF01` | The one accent. Primary action, focus ring, active layer, the crosshair. |
| `--lime-press` | `#B2E200` | Press/hover value shift. Never a second accent. |

### 1.2 Graphite ramp — SORA extension (dark sheets)

| Token | Hex | Role |
|---|---|---|
| `--graphite-900` | `#0A0C0D` | Well: recessed troughs, fields at rest, table bodies, trace wells. |
| `--graphite-800` | `#121517` | The default sheet. ~75% of the app's area. |
| `--graphite-700` | `#191D20` | Raised: headers, sticky rails, hovered rows, active cells. |
| `--graphite-600` | `#21262A` | Alt sheet — secondary panels, legend blocks. |
| `--graphite-500 / 400` | `#2D3439` / `#3D464C` | Field borders, strong hairlines, focused boundaries. |

Dark ink: `--text-hi #EEF1F3` (15.4:1 on sheet) · `--text-mid #9FA9B1` (7.6:1) ·
`--text-low #7B858D` (4.8:1, permitted at ≥12px only).

### 1.3 SAIL ramp I→VI — designed first, everything else stays out of its way

Constraint set: greenless (green means *safe*; SAIL I means *low*), colour-blind safe by
luminance and by form, and **no hue between 95° and 150°** so a risk state can never be
confused with the lime accent. It is a temperature ramp: nothing is lit at I, everything
is lit at VI.

| Token | Dark | Ink on fill | Reads as |
|---|---|---|---|
| `--sail-1` | `#8A95A1` | black, 9.4:1 | Cold steel — unlit |
| `--sail-2` | `#A79B93` | black, 10.4:1 | Warm grey |
| `--sail-3` | `#C99A3F` | black, 9.4:1 | Brass / caution |
| `--sail-4` | `#DD7F31` | black, 8.2:1 | Amber |
| `--sail-5` | `#D4502F` | white, 4.6:1 | Vermilion |
| `--sail-6` | `#B82633` | white, 6.3:1 | Signal red |

Fills and 2px bands only in dark theme — `--sail-6` as 13px type on a graphite sheet is
3.1:1 and fails. The light ramp (`#566270 · #6D6158 · #8A6410 · #A0511A · #B2361A ·
#9C1726`) clears 4.5:1 as type on paper, so in light theme the ramp may also be ink.

**Colour never carries SAIL alone.** `SailBadge` always shows three redundant encodings:
the Roman numeral, a six-segment bar with *n* filled, and a plate geometry change —
I–II square / III–IV one notched corner / V–VI notched plus a 2px outer band. Greyscale
and CVD legibility come from the form.

### 1.4 ARC band and status

ARC a–d: `#7D8894 · #6F93AD · #4F86B8 · #2F6EA8` — one hue, rising chroma, distinct from
both the lime and the SAIL ramp. Status (draft / determined / dossier ready / submitted /
authorised) is **not** coloured at all: one ink level and five glyph shapes, because a
submission status is not a risk reading. `--warn` and `--fail` are aliases of `--sail-3`
and `--sail-6`, not new values.

---

## 2. Typography

**Archivo** (everything) + **Outfit Light 300** (wordmark and the landing display line
only). Inherited from Dronex; both Google Fonts.

The brief asks for tabular lining numerals, a real weight range, and 11–13px legibility.
Archivo delivers all three — it is a grotesque drawn for signage and interface use with
`tnum` and 100–900 weights, and its numerals are unambiguous at 11px.

**There is no monospace in this system.** Dronex ships none, and the brief explicitly
forbids a mono face used decoratively on things that are not data. So the
machine-derived register — engine outputs, citations, coordinates, rulebase hashes — is
marked *structurally* instead of typographically: it sits in a recessed `--sheet-well`
block, under an 11px/0.1em caps micro-label, set in Archivo 500 with
`font-variant-numeric: tabular-nums`. Alignment comes from `tnum`, authority comes from
the well. This is the stronger answer: the register is visible even in greyscale print,
and nothing is cosplaying as a terminal.

### Type scale

| Role | Family / weight | Size / line-height | Tracking |
|---|---|---|---|
| Display (landing hero) | Outfit 300 | 60 / 1.04 | −0.035em |
| Display mobile | Outfit 300 | 36 / 1.08 | −0.03em |
| H1 page title | Archivo 600 | 32 / 1.12 | −0.02em |
| H2 section | Archivo 600 | 24 / 1.2 | −0.015em |
| H3 panel title | Archivo 600 | 18 / 1.3 | −0.01em |
| H4 sub-panel | Archivo 600 | 15 / 1.35 | 0 |
| Body L | Archivo 400 | 18 / 1.6 | 0 |
| Body | Archivo 400 | 15 / 1.55 | 0 |
| Body S | Archivo 400 | 13 / 1.5 | 0 |
| Label | Archivo 600 | 12 / 1.3 | 0.1em, caps |
| Micro-label | Archivo 600 | 11 / 1.25 | 0.1em, caps |
| Data | Archivo 500 tnum | 14 / 1.4 | 0 |
| Data S | Archivo 500 tnum | 12 / 1.4 | 0 |
| Figure (verdict) | Archivo 700 tnum | 72 / 1 | −0.03em |
| SAIL numeral | Archivo 600 | 40 / 24 / 14 | 0.02em |

Prose measure 68ch. Headlines wrap to 2–4 lines on purpose. Caps live in exactly two
places: 11–12px data labels, and the domain acronyms, which are caps because that is
their spelling — never as a tracked-out eyebrow over a section heading.

---

## 3. Layout

**Spacing** — 4px base: `2` (sheet gap, structural only) · `4 8 12 16 20 24 32 40 48 64 96`.
Panel padding 20–24; page margins 48 desktop / 16 mobile; section rhythm 96 marketing,
32 app.

**Radius** — Dronex's three, plus one: `0` sheets, panels, SAIL plate, table cells ·
`2px` buttons, inputs, chips · `10px` media frames, drawers, map canvas, mobile cards ·
`999px` pills and circular badges.

**Elevation** — no shadow in the flat plane. Depth is material: recessed `--sheet-well`,
flush `--sheet`, raised `--sheet-raised`, separated by the 2px black gap. One shadow token
(`--shadow-overlay`) exists for things that leave the plane — modal, drawer, map popover —
always with a scrim. If something needs a shadow to be seen, its sheet level is wrong.

**Marketing grid** — 1440 frame, 1240 max, 12 columns, 24 gutters, 48 margins. Sections
are asymmetric sheet bands sized by their media ratio (16:9 hero, 4:3 half-band, 3:4
portrait, 1:1 inset), butted with the 2px gap. Not a three-up card grid.

**App grid** — 240px fixed rail (64px icon rail below 1200), fluid canvas, panels butted
with the 2px gap, 16px canvas gutter. The verdict screen breaks it: fluid left (badge +
derivation tree) and a sticky 420px right column (chain + counterfactual).

**Mobile 390** — single column, 16px margins, 56px bottom tab bar, 44px minimum targets.
The map step is a full-bleed chart canvas with a draggable sheet at three detents
(88 / half / full) carrying layers and area readout. The derivation tree becomes a
vertical indented outline with identical node anatomy — collapsed in form, complete in
information.

**Marketing ↔ product** — same tokens, same sheets, same gaps. The difference is density
and media: marketing runs 96px rhythm with one idea per screenful and photography; the
app runs 16–24px rhythm with no photography at all. The landing capability sections are
the app itself, in its own palette, so arriving at the product is continuous. The one
object that appears identically in both is the `SailBadge`.

---

## 4. Motion

Curves — `--ease-ui cubic-bezier(.22,.61,.36,1)` (Dronex) · `--ease-exit
cubic-bezier(.4,0,1,1)` · `--ease-instrument cubic-bezier(.16,1,.3,1)` for anything
representing a computation or a physical volume.

Durations — `--t-tap 90ms` · `--t-ui 160ms` · `--t-panel 240ms` · `--t-media 420ms` ·
`--t-compute 1200ms`.

| Screen | The one orchestrated moment |
|---|---|
| Landing | The risk chain assembles left→right, one link per 90ms, once on load |
| Category checker | Verdict plate snaps in, estimated SAIL segments fill |
| Operations dashboard | None. It is a list. |
| Intake wizard | Step transition: 12px slide + fade, stepper tick advances |
| Map step | Contingency volume and ground-risk buffer extrude outward from the flight geography, 420ms, `--ease-instrument` |
| Verdict | **The derivation tree draws itself edge by edge**, leaves→root, nodes settling 40ms behind their incoming edge; the badge resolves last, its figure counts up once |
| Counterfactual applied | The chain re-reads; the badge steps down one plate at a time, 180ms per step |
| Dossier builder | Section rows tick complete as generation streams |
| Computation progress | Stages reveal sequentially with elapsed time — the waiting state *is* the orchestration |

`prefers-reduced-motion: reduce` → all of the above become 1ms; the tree renders complete,
the figure renders final, volumes render at final geometry. No information lives in
motion alone. Forbidden: parallax, spring, scroll choreography, shimmer, spinners.

---

## 5. Principles

1. **Colour is a reading, not a style.** Coloured = encoding risk, or offering the one
   primary action. Everything else is ink on sheets.
2. **Depth is material, not optical.** Well, sheet, raised, 2px ground-through gap. No
   shadows, no glass, no float.
3. **Show the working.** Every determination carries its rule, citation, inputs and
   rulebase stamp within one interaction of the number itself.
4. **Density is earned, not uniform.** Large quiet sheets, then one dense instrument
   object carrying the screen.
5. **The tool does not grant anything.** The boundary between what the LLM extracted and
   what the engine concluded is drawn in the interface, not disclaimed in a footer.

---

## 6. Map surface — the choice you made

A **designed vector chart surface**, drawn in-page: no tiles, no network, no key. It
renders a graticule, a coastline/terrain abstraction, population-density cells as a
hatched concrete overlay, ED-269 geo-zones as hairline polygons with lime edges, and the
three operational volumes (flight geography / contingency / ground-risk buffer) as
concentric offsets. Implementation note for the engineer: this is a MapLibre *style*, not
a basemap — the same layer stack points at a vector source in production, and the design
holds offline and in a printed dossier.

---

## 7. Media

Eleven slots from §5 of the brief plus four the design added (`chain-diagram`,
`checker-result`, `app-shell`, `persona-strip`). Every placeholder reserves exact aspect
ratio, uses the Dronex crop-mark motif rather than a grey box, and shows its slot id in
dev mode. Full table in `media-manifest.md`.

---

## 8. Self-critique — defaults caught and killed

1. **Green→red risk ramp.** The default, wrong twice: green encodes *safe* when SAIL I
   only means *low*, and green/red is the worst CVD pairing. → Greenless temperature ramp
   plus numeral + segment count + plate geometry, so colour is never load-bearing.
2. **Status pills reusing risk colours.** Implies submission state is a risk reading. →
   One ink level, five shapes.
3. **Landing as hero + three-up feature grid.** → Asymmetric sheet bands whose proportions
   come from the media ratios you specified. The hero's job is the chain, not a slogan.
4. **A decorative monospace for "technical" things.** → No mono at all; the machine-derived
   register is marked by a recessed well and a caps micro-label.
5. **Spinner for the engine run.** → `ComputationProgress`: named stages with elapsed time,
   because a compliance officer wants to see which stage is slow.
6. **A "trusted by" logo bar above the fold.** → `proof-logos` renders low, labelled
   "Referenced frameworks", with the no-endorsement note inline.

Deliberately unchanged: the SAIL badge is large and chromatic and will be the first thing
anyone notices. In a palette this quiet, that is the point.

---

## 9. What the three answers changed

| Answer | Effect |
|---|---|
| Full Dronex inheritance | Palette rebuilt on black/paper/concrete/lime; IBM Plex dropped for Archivo + Outfit; monospace removed entirely and replaced with a structural data register; theme model became "the ground never changes, the sheets flip"; the advisory-cyan rationale is gone and lime now carries interactive affordance, held in check by a one-primary-action-per-view rule. |
| Designed chart surface | Map step ships as a vector chart with full layer control, no tiles; works offline and in the dossier. Specified as a MapLibre style so production swaps the source, not the design. |
| All screens, one delivery | Uniform fidelity across all sixteen areas at 1440 and 390, dark and light. The verdict screen and the map step still get the two orchestrated moments; nothing else is given showpiece treatment. |
