# SORA Copilot — components

Every component below is implemented in `SORA Copilot.dc.html`, `SailBadge.dc.html` or
`MediaSlot.dc.html`. Values reference tokens from `tokens.css` / `tailwind.theme.ts`;
no component carries a hard-coded colour, size, radius, shadow or duration.

Conventions used throughout:

- **Focus** is global: `*:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px }`.
  No component overrides it.
- **Disabled** is `opacity: .35; cursor: not-allowed; pointer-events: none` — never a
  colour change, because colour means risk here.
- **Press** is `transform: scale(.98)` over `--t-tap`. No lift, no glow.
- **Minimum target** 44px on anything clickable, including icon-only buttons.
- Shape or label always accompanies colour. No state is colour-only.

---

## SailBadge

The identity object. Appears in marketing, dashboard rows, the derivation tree root, the
counterfactual cards and the checker result — identical in all of them.

| Prop | Type | Default | Notes |
|---|---|---|---|
| `level` | `1\|2\|3\|4\|5\|6` | `1` | Clamped. Rendered as a Roman numeral. |
| `size` | `'sm'\|'md'\|'lg'` | `'md'` | 40 / 64 / 132 px square. |

**Three redundant encodings, always on:** the Roman numeral; a six-segment bar with
`level` segments filled; and plate geometry — `I–II` square, `III–IV` one notched corner
(14px), `V–VI` notched plus a 2px inset outer band. Fill is `--sail-{n}`, ink is
`--sail-{n}-ink`. Radius `0`. `role="img"` with `aria-label="SAIL III of VI"`.

States: no hover or active — it is a readout, not a control. When it changes as a
counterfactual is applied it steps one level at a time, 180ms per step (`sail-step`).
`sm` hides the "SAIL" caption; the numeral and segments remain.

---

## RiskChainReadout

Horizontal row of five cells — iGRC, GRC, ARC, residual ARC, SAIL — butted with the 2px
sheet gap, wrapping at narrow widths.

| Prop | Type | Notes |
|---|---|---|
| `links` | `{ key, value, note }[]` | Exactly five; `key` is the domain term verbatim. |
| `animate` | `boolean` | Assembles left→right, 90ms per link, once. |

Each cell: 11px caps label, 28px `tnum` figure, 11px note naming the inputs. States:
default; `recomputing` (figures drop to `--text-low`, note replaced by "re-running");
`stale` (2px top band in `--sail-3` and the note "rulebase changed").

---

## DerivationTree / DerivationNode

`DerivationTree` lays nodes on a fixed 960×520 canvas (desktop) with an SVG edge layer
behind, or as an indented outline (mobile, `<480px`). Edges draw leaves→root via
`stroke-dashoffset`; each node settles 40ms behind its incoming edge.

| Prop | Type | Notes |
|---|---|---|
| `nodes` | `DerivationNode[]` | |
| `edges` | `{ from, to, emphasis?: 'default'\|'accent' }[]` | Accent edges are the two that produce SAIL. |
| `orientation` | `'graph'\|'outline'` | Outline is the mobile treatment, not a degraded one. |
| `onReplay` | `() => void` | |

`DerivationNode` variants: `fact` (leaf — sheet, hairline border, 10px FACT label),
`derived` (raised sheet, strong border, term + value + rule sentence + `CitationChip`),
`root` (2px accent border, contains a `SailBadge md`).

States: default · hover (border → `--hairline-strong`) · focus (global ring) ·
expanded/collapsed (chevron, children animate over `--t-panel`) · `changed` (2px left
band in `--accent` after a counterfactual re-run) · loading (node plate at 45% opacity,
no text) · error (left band `--sail-6`, "rule did not resolve").

---

## CitationChip

Pill, hairline `--accent-line` border, 10px label, 22–24px tall. Content is the clause
reference verbatim (`AMC1 Art.11 · Table 2`). Props: `reference`, `href?`, `size`.
Hover reveals the full clause title in a popover; click opens the rulebase at that clause.
Never truncates a reference — it wraps instead.

---

## RobustnessPill

`Low` / `Medium` / `High`. Pill, 24–28px, 10px caps, hairline border. **High** additionally
fills `--sheet-alt` so the three levels differ by fill as well as by word. Props:
`level`, `required?` (shows a 2px left band when the claimed level is below required).

---

## OsoRow / OsoMatrix

`OsoMatrix` is a wrapping grid (`minmax(300px, 1fr)`) of `OsoRow`s on the 2px gap,
grouped by robustness when `groupBy="robustness"`.

| Prop | Type | Notes |
|---|---|---|
| `id` | `string` | `OSO #05`, `tnum`, fixed 58px column. |
| `name` | `string` | |
| `robustness` | `'Low'\|'Medium'\|'High'` | |
| `status` | `'evidenced'\|'partial'\|'gap'\|'not-applicable'` | glyph `▣ ◧ □ ⊘` + word + ink. |
| `onOpen` | `() => void` | Opens `OsoDetailDrawer`. |

States: default · hover `--sheet-raised` · focus · selected (inset 2px accent) ·
loading (plate, no text) · empty (matrix shows `EmptyState` "No OSOs — run a determination
first").

---

## MitigationCard

M1 / M2 / strategic. Header (name + GRC or ARC delta), a three-way robustness selector,
and an evidence line. A robustness level the operator cannot currently claim is
**disabled**, not hidden, so the path to it is visible.

Props: `code`, `label`, `delta`, `claimed`, `maxClaimable`, `evidence: {label, status}`,
`onChange`.

---

## CounterfactualCard

Props: `title`, `effect` (chain delta, set in `--accent`), `resultSail`, `cost`,
`applied`, `onApply`.

States: default · hover · applied (button fills `--accent`, label becomes
`APPLIED · UNDO`) · unavailable (disabled with the blocking reason in place of `cost`) ·
loading (button label `RE-RUNNING`, card non-interactive).

---

## MapVolumeEditor

The designed chart surface: graticule, terrain abstraction, then five toggleable layers —
flight geography (accent fill), contingency volume (dashed accent outline), ground risk
buffer (`--sail-4` outline), population density (hatched `--hairline`), ED-269 geo-zones
(`--arc-c`). On derive, the three volumes extrude outward over `--t-media`.

| Prop | Type | Notes |
|---|---|---|
| `layers` | `Record<LayerKey, boolean>` | |
| `onToggleLayer` | `(k: LayerKey) => void` | |
| `geometry` | `GeoJSON` | |
| `readout` | `{ fg, cv, grb, peakDensity }` | Areas in km², `tnum`. |
| `adjacentWarning?` | `string` | Renders the `--sail-3` advisory block. |

Mobile: full-bleed canvas with a draggable sheet at three detents (88px peek / half /
full) holding `DensityLegend`, layer control and readout. Zoom controls are 44px.

States: empty (no geometry — "Draw the flight geography to begin", draw tool primed) ·
drawing · deriving (volumes animate in) · error (tile/derive failure, retry) · offline
(last-synced geometry, controls disabled with a reason).

---

## DensityLegend

Five hatch swatches with population bands (`<5`, `5–50`, `50–500`, `500–5,000`, `>5,000`
ppl/km²), density expressed by hatch spacing, not by hue. Props: `bands`, `peak`,
`unit`.

---

## FactChip

The boundary between the LLM and the engine. A fact extracted from prose, rendered with a
3px left band: `--sail-3` unconfirmed, `--accent` confirmed, `--hairline-strong` rejected
(text struck through, `--text-low`).

Props: `text`, `state: 'unconfirmed'|'confirmed'|'rejected'`, `source`, `onConfirm`,
`onReject`, `onEdit`.

Only the unconfirmed state shows the CONFIRM / REJECT pair. A confirmed chip keeps an
`EDIT` affordance; nothing silently re-enters the unconfirmed state. The word
UNCONFIRMED / CONFIRMED / REJECTED is always present — the band colour never carries it
alone.

---

## WizardStepper

Seven steps, horizontal on desktop, horizontally scrollable on mobile. Tick states:
upcoming (hairline ring, `--text-low`), current (filled `--accent`, ink numeral),
complete (`--sheet-alt` fill, `--text-hi`). Props: `steps`, `current`, `onGo`,
`furthestReached` (steps beyond it are disabled).

---

## StatusPill

Deliberately **not** on the risk ramp. One ink level, five glyphs:
`draft □` · `determined ■` · `dossier ready ◆` · `submitted ◧` · `authorised ▣`.
Props: `status`, `size`. Hover and focus only when it is a filter control.

---

## RulebaseStamp

`Rulebase 2026.2 · 01 Oct 2026`, Archivo 500 `tnum`, 12px, `--text-low`, with a 7px
`--accent` square when the stamp is authoritative for the determination on screen.
Props: `version`, `date`, `pinned`, `emphasis: 'quiet'|'authoritative'`.
Appears on: verdict, dossier preview, every export header, the app rail, the landing
hero and footer.

---

## DisclaimerBanner

A structural component, not a footer line. 3px left rule, 13px `--text-mid`, the fixed
string verbatim. Variants: `inline` (verdict, dossier preview), `footer` (accent rule on
black ground), `export` (ink on paper, repeated in every generated page header).
Props: `variant`. No dismiss affordance — it is never dismissible.

---

## MediaSlot

Reserves the exact aspect ratio, so the real asset lands with zero layout shift.
Placeholder: `--sheet-well` fill, a 48px graticule at 50% opacity, Dronex crop marks at
all four corners, and a centred block — accent square, `KIND · INTRINSIC SIZE` micro-label,
a sentence describing the asset. `dev` adds the slot id as a lime chip.

Props: `slot`, `kind: 'image'|'video'|'illustration'`, `ratio`, `size`, `note`, `dev`.

States: placeholder (above) · loading (graticule only) · loaded (asset, `object-fit: cover`,
radius `--radius-md`, filter `saturate(.95) contrast(1.02)`) · error (crop marks in
`--sail-6`, "asset failed to load", slot id shown regardless of `dev`).

---

## EvidenceUploader

Dashed `--hairline-strong` border, radius `--radius-sm`, centred prompt, a primary pill,
and a constraints line (formats, 40 MB, storage region). States: idle · dragover (border
and prompt switch to `--accent`) · uploading (per-file row with a determinate bar in
`--accent`) · success (file row with `▣`) · rejected (`--sail-6` left band, the reason
stated — size, format or virus scan).

Props: `accept`, `maxBytes`, `region`, `files`, `onAdd`, `onRemove`.

---

## DossierSectionRow

Glyph + name + right-hand meta. Glyph/ink: complete `▣ --accent`, partial `◧ --sail-3`,
not started `□ --text-low`. Props: `name`, `state`, `meta`, `onOpen`.
States add hover, focus and `generating` (meta becomes an elapsed counter).

---

## EmptyState

Props: `slot` (a `MediaSlot` illustration), `title`, `body`, `action`, `secondaryAction?`.
Body copy always says what the next concrete step produces, never "get started".
Used by: operations, dossiers, fleet, evidence vault, search results.

---

## ComputationProgress

The engine's waiting state. Named stages in order — Facts validated · iGRC resolved ·
Ground mitigations applied · Airspace assessment · SAIL and OSO set · Containment check —
each with a glyph and a per-stage elapsed time in `tnum`. The running stage carries a 2px
`--accent` left band; queued stages sit at 45% opacity. A total elapsed line sits below
with the note that the run continues if you leave.

Props: `stages: {label, state: 'done'|'running'|'queued'|'failed', ms?}[]`, `elapsedMs`,
`onCancel?`. States: running · failed at stage N (that stage takes a `--sail-6` band and
the remainder is marked not run) · complete (collapses into the verdict).

No spinner. No shimmer. Skeletons are static blocks at stepped opacity.

---

## Shared primitives (shadcn/ui layer)

- **Button** — `primary` (fill `--accent`, ink `--accent-ink`), `secondary` (transparent,
  1px `--hairline-strong`), `ghost`, `destructive` (fill `--sail-6`, white ink).
  Shapes: `pill` on marketing, `--radius-sm` in the app. Sizes 36 / 44 / 48px.
  Hover is a value shift only (`--accent-press`, or a `--sheet-raised` wash on secondary).
- **Input / Select / Textarea** — `--field-bg`, 1px `--field-border`, `--radius-sm`,
  44–48px, 12px caps label above. Error adds a 1px `--sail-6` border and a message row;
  the message is always present, never a colour-only error.
- **Toast** — `--sheet-raised`, `--shadow-overlay`, 3px left band: `--accent` success,
  `--sail-3` warning, `--sail-6` failure, plus one action. Auto-dismiss 6s, paused on
  hover or focus, never for failures.
- **Modal / AlertDialog** — `--sheet-raised` on a `--scrim` backdrop, `--shadow-overlay`,
  `--radius-md`. Destructive dialogs take a 3px `--sail-6` top rule and require typing the
  record name; the confirm button stays disabled until it matches.
- **Drawer** — right, 480px desktop / full-height sheet on mobile, 2px ground-coloured
  left edge instead of a border.
