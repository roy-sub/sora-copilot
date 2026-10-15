# SORA Copilot — Session Handoff

> **For the incoming Claude session.** This file plus the repo `roy-sub/sora-copilot` is the full context. Read this file completely, then the files it points to, before writing any code. The repo's `main` branch is the **base truth**: every upgrade gets committed and pushed there.

---

## 0. The owner and how to work with them

- Owner: GitHub `roy-sub`. Codes mostly in Python, specialises in AI automations, workflows, agents and SaaS.
- **Keep explanations short and to the point.**
- **Git workflow:** commit straight to `main` and push (`git push -u origin main`). No PRs unless asked.
- Commit message trailer: whatever attribution the new session's system prompt asks for.
- **Ask before you start if anything is unclear.** On choices that are clearly yours to make, pick the opinionated option and say so in a line.

---

## 1. What the product is

**SORA Copilot** is a European aviation-compliance web app for professional drone operators. Under EU 2019/947, a "specific category" drone flight (BVLOS, over people, near aerodromes) needs a **SORA**: a formal risk assessment submitted to the national aviation authority (NAA). A consultant charges €1,000–5,000 for one. SORA Copilot does it instead. The operator describes the mission, a deterministic rules engine computes the official risk chain, and the app emits an authority-ready dossier in which every conclusion cites its rule.

The chain, in the operator's vocabulary. **Never soften these terms into "score" or "level".**

```
drone size + speed + what's underneath → iGRC (1–10)
  + mitigations M1(A)/M1(B)/M1(C)/M2   → GRC (final ground risk class)
airspace + altitude + aerodrome        → ARC (a/b/c/d)
  + strategic mitigation               → residual ARC
GRC × residual ARC                     → SAIL (I–VI)
SAIL                                   → OSO set at Low/Medium/High robustness, then containment
```

**Fixed strings. Use them verbatim:**
- Product name: **SORA Copilot**
- Primary promise: **From mission to dossier in minutes.**
- Audit promise: **Every line cites its rule.**
- Disclaimer, on the verdict screen and in every export: *SORA Copilot prepares and verifies your risk assessment. Your national aviation authority grants the authorisation.*
- Rulebase stamp: *Rulebase 2026.2 · 01 Oct 2026* (from `RULEBASE` in `src/engine/rulebase.ts`)

**Voice:** like a pre-flight checklist. Sentence case, active voice, no exclamation marks.

**Never use these words:** effortless, seamless, magic, AI-powered, revolutionise, unlock, empower, game-changing, supercharge.

**Users:**
- a two-person inspection company in Graz
- a solo BVLOS operator
- a compliance officer who reads the trace before the verdict
- eventually, an NAA case officer reading the dossier

The success moment: a compliance officer expands three nodes of the derivation tree, finds the citation on each, and stops being suspicious.

---

## 2. Where it came from

The project started as a **Claude Design handoff bundle**, now in `design/`:

| File | What it is |
|---|---|
| `design/HANDOFF.md` | The bundle's original README |
| `design/chats/chat1.md` | Transcript of the design conversation (what the user wanted) |
| `design/project/SORA Copilot.dc.html` | **The primary prototype.** 1,336 lines; every screen, inline styles, plus a JS logic block at the bottom with all demo data |
| `design/project/uploads/SORA Design Brief.md` | **The full product brief.** Read §1–§9 |
| `design/project/design-plan.md` | Palette, type, layout, motion and principles |
| `design/project/tokens.css` | Token source. Copied to `src/styles/tokens.css` with font variables changed |
| `design/project/components.md` | Every component: variants, states, props |
| `design/project/motion.md` | Named animation presets and the verdict sequence |
| `design/project/media-manifest.md` | Every MediaSlot: ratio, size, content |
| `design/project/SailBadge.dc.html`, `MediaSlot.dc.html` | Component prototypes |
| `design/project/_ds/…` | Dronex design system (inherited brand: black/paper/concrete/lime, Archivo + Outfit) |

The prototype is HTML, not production code. The job is to **recreate it pixel-faithfully** in the real stack, not to copy its structure.

### Design rules that must hold everywhere
- **The ground is always black, in both themes.** Only the sheets flip: graphite in dark, paper in light. `data-theme` sits on `<html>`; dark is the default.
- **The 2px gap is structural.** Panels sit side by side with the black ground showing through as a hairline (`gap-sheet` = 2px).
- **Depth comes from material, not shadow.** The levels are well, sheet, raised and alt. Only overlays leaving the page (modal, drawer, toast) get a shadow, `shadow-overlay`.
- **Colour encodes risk or the one primary action.** Lime (`--accent`) is reserved for the primary action and the focus ring. The SAIL ramp is greenless.
- **Colour is never the only signal.**
  - The SAIL badge always shows three encodings: the numeral, a six-segment bar, and a plate shape. I–II is square, III–IV has a notched corner, V–VI is notched with an inset band.
  - Status pills use one ink colour and five glyphs: `□ ■ ◆ ◧ ▣`.
  - Evidence states use glyph plus word: `▣` evidenced, `◧` partial, `□` gap, `⊘` not applicable.
- **Accessibility floor:**
  - AA contrast
  - visible focus ring (global in tokens.css)
  - 44px minimum touch targets
  - `prefers-reduced-motion` honoured (global in tokens.css, plus `useReducedMotion` for Framer Motion)
- **No monospace font.** Machine-derived data uses Archivo 500 with tabular numbers, set in a recessed well under an 11px caps micro-label.
- **Motion:** one orchestrated moment per screen. No spinners, no shimmer, no spring or bounce, no parallax.
  - Verdict: the derivation tree draws itself leaves→root over about 1200ms.
  - Map: the volumes extrude outward.
  - Landing: the chain assembles left→right.
  - Counterfactual applied: the SAIL badge steps one plate at a time, 180ms per step.
- **MediaSlot placeholders:** exact aspect ratio, graticule background, crop marks, kind/size micro-label, a note. The slot id only shows with `?slots=1`. The owner adds real media later.

---

## 3. Decisions the owner made (do not reopen)

| Question | Decision |
|---|---|
| Stack | **Next.js 15 App Router, static export** (`output: "export"`), Tailwind v4, shadcn-style primitives on Radix, Framer Motion |
| Structure | **Real routes, responsive.** No review toolbar. Breakpoints replace the prototype's 1440/390 toggle. Theme toggle lives in Settings. `?slots=1` shows MediaSlot ids |
| Map and derivation tree | **In-page SVG as designed.** No MapLibre or React Flow for now |
| Data / engine | **Real SORA 2.5 engine**, not static mocks |
| Repo | `roy-sub/sora-copilot`, branch `main`, push directly |

---

## 4. Running it

```bash
npm ci
npm run dev        # http://localhost:3000
npm test           # 9 engine tests, node:test with --experimental-strip-types (Node 22)
npm run build      # static export to out/; also type-checks
```

**Gotchas already hit:**
- **TypeScript is pinned to 5.9.x.** TS 7 breaks `next build` with "Cannot read properties of undefined (reading 'fileExists')". Do not upgrade it.
- **Engine and data files import each other with `.ts` extensions** (`allowImportingTsExtensions`), so `node --test` can run them without a bundler. UI files use the `@/` alias.
- **`trailingSlash: true`.** Internal links end in `/`. `usePathname()` is normalised by `usePath()` in `Shell.tsx`.
- **Dynamic routes need `generateStaticParams`.** Operations created on the device use `/app/operations/view/?id=…`, a pre-generated `view` param that reads the search param inside `<Suspense>`. Use `opHref(id)` from `components/verdict/Verdict.tsx` to build links.
- **There is no backend.** All workspace mutations persist to `localStorage` through `WorkspaceProvider` (`src/lib/workspace.tsx`, key `sora.workspace.v1`). Wrap any `localStorage` access in try/catch.
- **Tailwind v4 is configured CSS-first in `src/app/globals.css`.**
  - The `@theme inline` block maps token variables to colours: `bg-sheet`, `bg-sheet-raised`, `bg-sheet-well`, `bg-sheet-alt`, `text-ink-hi/mid/low`, `bg-accent`, `text-accent-ink`, `border-hairline(-strong)`, `bg-sail-1..6`, `arc-a..d`, `bg-field`, `border-field-border`, `bg-scrim`.
  - Type-role utilities: `t-micro`, `t-micro-10`, `t-h1..h4`, `t-body-lg/body/body-sm/cap`, `t-data/data-13/data-sm`, `t-figure`, `t-display` (responsive 36 → 60px), `tnum`, `pretty`, `no-scrollbar`, `shadow-overlay`, `tr-ui`, `press`.
  - Breakpoints: `sm` 480, `md` 768, `lg` 1024, `rail` 1200.
  - **Never add Tailwind theme variables that share a name with a token** (`--text-*`, `--radius-*`, `--shadow-*`, `--ease-*`). That creates circular CSS variables.
  - `project/tailwind.theme.ts` from the bundle is reference only and is superseded by `globals.css`.
- **Fonts:** `next/font` self-hosts Archivo (400–700) and Outfit 300. `tokens.css` reads them from `--font-archivo` and `--font-outfit`. Outfit is only for the wordmark and display lines (`font-display`).

---

## 5. Code map

```
src/engine/            PURE, deterministic, no React. The product's credibility lives here.
  types.ts             OperationInput, Determination, TraceNode, OsoRequirement, Outcome
  rulebase.ts          SORA 2.5 tables + CITE citation strings + RULEBASE stamp  ⚠ verify
  engine.ts            determine(input) → Determination with trace; counterfactuals(input, fitted)
  checker.ts           checkCategory({mass, ground, operation}) → open A1/A2/A3 | specific + SAIL | certified
  geometry.ts          corridor buffers (bufferOutline), areas, deriveVolumes, analyse (peak density,
                       adjacent populated cell + compass direction), nearestOnLine, rectDistToLine
  engine.test.ts       9 tests; all fixtures reproduce their SAILs
src/data/
  fixtures.ts          FLEET (4 aircraft), OPERATIONS (6 ops with full inputs), EVIDENCE, ORG, POWERLINE_INPUT
  oso.ts               plain-language "what it requires" + evidence checklist per OSO; ASSURANCE per robustness
  map.ts               16×10 km chart scene: DEFAULT_LINE corridor, CELLS (500 m population grid),
                       GEO_ZONES (AT-R-114), AERODROME (LOWG, off-chart), RIVER, ROAD
  marketing.ts         TIERS (5 pricing tiers), FAQ (5)
src/lib/
  prefs.tsx            theme (data-theme + localStorage, init script before paint), slots dev flag
  workspace.tsx        WorkspaceProvider: inputs overrides, created ops, evidence, files, dossiers versions,
                       rulebasePin, region, aircraft; helpers op(), setInput, addOperation, setEvidence, addDossier
  determine.ts         determinationOf(op) memoised; drafts return null
  cn.ts                clsx + tailwind-merge
src/components/
  Brand.tsx            Wordmark, RulebaseStamp, Disclaimer (inline|footer), CitationChip, RobustnessPill,
                       StatusPill, EvidenceMark/EVIDENCE_TONE, DISCLAIMER/STAMP constants
  SailBadge.tsx        SailBadge (sm 40 / md 64 / lg 132), SailPlaceholder, SailScale, useSteppedLevel (sail-step)
  MediaSlot.tsx        placeholder/loaded states, `src` prop for when real assets land
  ComputationProgress  useStagedRun + <ComputationProgress> (6 named stages, elapsed time, failAt for error demo)
  Toast.tsx            ToastProvider/useToast — tone ok|warn|fail, 6s auto-dismiss paused on hover/focus, never for fail
  ui/Button.tsx        Button / ButtonLink / buttonClass — primary|secondary|ghost|destructive, shape sm|pill, md 44|lg 48
  ui/Field.tsx         FieldLabel, Input, Select, Textarea, Segmented (radiogroup), RadioRow
  ui/Dialog.tsx        Modal (destructive variant), Drawer (right, 480px), DialogClose — Radix
  app/Shell.tsx        AppShell: rail 240px (≥1200) / 64px icon rail (768–1199) / bottom tab bar (<768); PageHeader; NAV
  app/EmptyState.tsx
  marketing/           Chrome (MarketingHeader variants nav|cta|stamp|plain, MarketingFooter), Faq, Tiers
  verdict/             Verdict (page logic + opHref), DerivationTree, Chain (RiskChainReadout + count-up once),
                       GapAnalysis (grouped High/Medium/Low), OsoDrawer (+ EvidenceUploader)
  wizard/MapVolumeEditor.tsx   ⚠ written, type-checks, NOT yet wired into any page (see §7)
src/app/
  layout.tsx                   fonts, theme init script, PrefsProvider, ToastProvider
  (marketing)/page.tsx         landing
  (marketing)/pricing|checker|legal
  (auth)/signin                magic-link + password (client-side demo)
  app/layout.tsx               WorkspaceProvider + AppShell
  app/page.tsx                 /app — operations dashboard
  app/fleet/page.tsx
  app/operations/[id]/         verdict (static params = fixture ids + "view")
design/                        the Claude Design bundle (reference)
```

---

## 6. The engine — what it does and why

`determine(input)` runs SORA 2.5:

- **iGRC (Table 2):**
  - The column is the first where *both* max dimension ≤ and max speed ≤ hold: 1m/25, 3m/35, 8m/75, 20m/120, 40m/200.
  - The row comes from peak population density: controlled area, <5, <50, <500, <5,000, <50,000, >50,000.
  - Ground environment `assembly` is forced into the >50,000 row.
  - MTOM ≤ 250 g and speed ≤ 25 m/s always gives iGRC 1.
  - A `null` cell, or a value beyond the last column, means outside SORA, which gives the certified outcome.
- **GRC (Table 5):**
  - M1(A) sheltering: low −1, medium −2.
  - M1(B) operational restrictions: medium −1, high −2.
  - M1(C) ground observation: low −1.
  - M2 impact dynamics: medium −1, high −2.
  - Levels the table doesn't offer **throw**. The UI shows them disabled, not hidden.
  - GRC is floored at the column's controlled-area value. GRC above 7 gives the certified category.
- **ARC (decision tree):**
  - Atypical airspace → a.
  - Above 150 m: controlled or TMZ → d; otherwise → c.
  - At or below 150 m in an aerodrome environment: class B/C/D → d; E/F/G → c.
  - TMZ → c. Controlled → c. Urban → c. Rural uncontrolled → b.
- **Residual ARC:** a strategic mitigation lowers ARC by one class (d→c, c→b, b→a).
- **SAIL (Table 7):** GRC row ≤2/3/4/5/6/7 × ARC a–d.
- **OSOs (Table 14):** 17 OSOs in SORA 2.5 (#01–09, 13, 16–20, 23, 24), each with a level per SAIL including `nr` (not required).
  - ⚠ The design copy said "~24 OSOs". That is SORA 2.0. We correctly use 17, computed with `OSO_TABLE.length`.
- **Containment:** returned as `assessment-required` with a note. **Not computed. Do not invent it.**
- **Trace:** ten nodes with fixed ids, which the tree layout depends on:
  - facts: `f-dim f-ground f-alt f-airspace f-aerodrome`
  - derived: `n-igrc n-arc n-grc n-rarc`
  - root: `root-sail`
  - Each derived node carries `rule`, `citation`, `inputs` and `detail`.
- **`counterfactuals(input, fitted)`:**
  - Generates single changes: M2 up (worded "the parachute fitted on {reg}" if one is fitted), M1(A) to medium, M1(B) up, claim strategic, lower altitude to 120 m if above 150 m, leave the aerodrome environment.
  - Re-runs the engine for each and keeps only those that lower SAIL, best first.

**Fixture SAILs, asserted in the tests:**

| Operation | Result | Basis |
|---|---|---|
| powerline-mur | III | Alta X 1.32 m, sparse 84 ppl/km² → iGRC 5; M1(A) low → GRC 4; LOWG aerodrome environment, class G → ARC c; strategic → b |
| roof-reininghaus | II | |
| quarry-peggau | II | |
| pipeline-leibnitz | IV | |
| thermal-werk2 | I | |
| schlossberg-event | certified | Draft; iGRC 8 over an assembly, GRC > 7 |

**Places where the real engine differs from the prototype's hand-typed values** (correctness wins; keep these):
- The checker's example (4–25 kg, sparsely populated, BVLOS) gives **SAIL IV**, not III.
- M2 has no "low" level.
- The prototype's ARC "c outside the aerodrome ring" contradicts the tree. We use the aerodrome-environment branch instead.
- Draft operations show a "Not run" placeholder plate instead of a SAIL.

⚠ **VERIFY BEFORE PRODUCTION.** The values in `rulebase.ts` and `oso.ts` were transcribed for this build. A competent reviewer must check them against the published JARUS SORA 2.5 text and national annex. Citations read `SORA 2.5 · Table N` and are kept next to the values in one file so that review is easy.

---

## 7. Status

### ✅ Done (on `main`, builds, 9/9 tests pass)
- **Tokens and theming:** dark/light, black ground, focus ring, reduced motion, fonts.
- **Landing `/`:** header nav, hero, stats, `hero-loop` slot, five-step chain explainer (assembles once), four capability sections with slots, personas, pricing, FAQ accordion, referenced-frameworks strip, footer with disclaimer.
- **`/pricing`:** five tiers and the "included at every tier" section.
- **`/checker`:** three real questions that run the engine. Result plate snaps in; shows open subcategory, or SAIL with iGRC/ARC/OSO count and a computed mitigation hint; mailto estimate.
- **`/legal`:** disclaimer, terms, privacy, rulebase changelog.
- **`/signin`:** magic link with validation and a sent state, plus a password form. Both route to `/app` (demo).
- **App shell:** responsive rail, collapsed rail and mobile tab bar; page header with search and notification buttons (not functional).
- **`/app` operations dashboard:** working status filters with counts, text filter, SAIL computed per row, status glyphs, mobile card layout, empty states.
- **`/app/fleet`:** table with computed kinetic energy. "Add aircraft" modal persists to the workspace.
- **`/app/operations/[id]` verdict:**
  - large stepped SAIL badge and risk chain with one-time count-up
  - SAIL scale
  - derivation tree: desktop 960×520 SVG with edge-draw and node-settle, an inspector with three nodes open by default, a mobile indented outline, and Replay
  - counterfactual advisor: "apply and re-run" overrides the inputs, the badge steps down, changed nodes get an accent band, Undo, and "Revert to recorded inputs"
  - rulebase stamp and disclaimer
  - Build dossier link to `/app/dossiers/?op=` — **that page does not exist yet**
  - Export trace (JSON download)
  - gap analysis grouped by robustness, with not-required OSOs listed
  - OSO drawer: requirement text, citation, evidence checklist that derives gap/partial/evidenced, drag-and-drop uploader that validates PDF/DOCX/XLSX up to 40 MB, mark not applicable, save with toast
  - draft operations get a "Run determination" screen with staged `ComputationProgress`
- **Map engine, `geometry.ts` + `data/map.ts`:** verified for the default corridor: FG 2.45 km², CV 4.44, GRB 8.48 km², peak 84 ppl/km², populated cell 279 m north of the buffer, AT-R-114 intersected, LOWG 7.4 km.
- **`components/wizard/MapVolumeEditor.tsx`:**
  - `MapCanvas`: SVG chart, graticule, hatched density cells, river and road, geo-zone, buffer outlines with extrude animation, draggable vertices, pan when zoomed, zoom ×1/2/4, scale bar, north marker, off-chart LOWG chevron
  - `useMapAnalysis`
  - `LayerControl`, `DensityLegend`, `AreaReadout`, `AdjacentWarning`
  - `MapSheet`: mobile draggable bottom sheet with three detents (88 / half / full)

### ⏳ Left, in this order
1. **Intake wizard `/app/new`.** This is the core flow and the next task. The nav already links here; it 404s today.
   - **Draft state:** a `WizardDraft` persisted to localStorage (`sora.wizard.v1`) so it is resumable ("Autosaved · resumable"). It holds: step, furthest step reached, aircraftReg, name, site, operationType, maxAltitudeM, durationMin, line `Pt[]`, fgHalfWidth, layers, ground environment, airspace (class, aerodromeEnvironment, modeS, atypical), mitigations, and fact chips.
   - **`WizardStepper`:** seven steps — Aircraft, Operation, Map, Ground, Airspace, Mitigations, Review.
     - Tick states: upcoming is a hairline ring; current is lime with the numeral in ink; complete is filled `sheet-alt`.
     - Steps beyond the furthest reached are disabled.
     - Scrolls horizontally on mobile.
     - Step transitions slide 12px in the direction of travel and fade (Framer `AnimatePresence`).
   - **Step 1, Aircraft:** radio cards from `ws.fleet`.
   - **Step 2, Operation:** name and site inputs; VLOS/EVLOS/BVLOS segmented control; altitude; duration. Note that above 120 m an airspace assessment is needed.
   - **Step 3, Map:** `MapCanvas` plus a side panel at 280px containing `LayerControl`, `AreaReadout`, `DensityLegend` and `AdjacentWarning`. On mobile, a full-bleed map with `MapSheet`.
     - Volumes come from `deriveVolumes(fgHalfWidth, aircraft.maxSpeedMs, maxAltitudeM)`.
     - Bump `extrudeKey` on vertex release.
     - Add a "Reset geography" button and a flight-geography width control.
   - **Step 4, Ground:**
     - Four `RadioRow`s: controlled, sparsely, populated, assembly.
     - Peak density comes from the map analysis.
     - Prefill the environment from the density band.
     - "Urban" is derived from populated or assembly.
   - **Step 5, Airspace:**
     - Class select A–G, defaulting to G.
     - Altitude band shown as derived.
     - Aerodrome proximity shown as derived ("7.4 km — LOWG Graz").
     - An "Inside aerodrome environment" checkbox, prefilled when within 5 NM, with the text "confirm against the national definition".
     - Mode-S/TMZ and atypical checkboxes.
     - Geo-zones intersected shown as chips with an `arc-c` border, derived from the map.
   - **Step 6, Mitigations:**
     - A `MitigationCard` for M1(A) (low/medium; high disabled), M1(B) (medium/high; low disabled), M1(C) (low only), M2 (medium/high; low disabled), and strategic (claimed / not claimed).
     - Each card shows its GRC/ARC delta and an evidence line. If the aircraft's `fitted` list includes a parachute, say so on the M2 card.
     - Show the live engine result, a small `SailBadge`, as feedback.
   - **Step 7, Review and confirm:**
     - Lead text: "Nothing below has reached the engine."
     - List every fact.
     - Unconfirmed extracted chips must be confirmed or rejected first; "Run determination" stays disabled until none are unconfirmed.
     - Running shows `ComputationProgress`, then `ws.addOperation({id: "op-"+Date.now(), status: "determined", rulebase: "2026.2", lastRun: "Just now", corridorKm, input})` and `router.push(opHref(id))`.
   - **Conversational intake panel**, brief §12. This is the visible boundary between the LLM and the engine.
     - Desktop: a 360px aside with a HIDE toggle. Mobile: a drawer opened from a button.
     - Contents: a prose box, an "Extracted facts — not yet in the engine" list, and an "Add detail" input.
     - **`FactChip`** has three states, each with a 3px left band and the state word always shown:
       - unconfirmed (`sail-3` band) — the only state with Confirm and Reject buttons
       - confirmed (accent band) — keeps an Edit action
       - rejected (`hairline-strong` band, struck through) — rejecting sends the user to the step that owns the fact
     - Confirming applies the value to the draft.
     - Extraction for now is a deterministic `extractFacts(text, fleet)` in `src/lib/extract.ts`, using regex and keywords for: aircraft model or registration, altitude, duration, VLOS/EVLOS/BVLOS, ground keywords (farmland/scattered → sparsely, town/residential → populated, crowd/event → assembly, fenced/closed site → controlled), airspace class, and corridor km. **Keep it behind an interface so an LLM call (Claude API) can replace it later.** The owner works in AI agents and will likely want this.
     - Seed the panel with the prototype's quote: "Alta X along the 110 kV line south of Gratkorn, about 14 km, below 120 metres, farmland and a few scattered houses." Chip states start as: aircraft confirmed, altitude and environment unconfirmed.
2. **Dossier builder `/app/dossiers/?op=`.** Use `useSearchParams` inside `Suspense`; default to `powerline-mur` and add an operation picker.
   - **`DossierSectionRow` list:** ConOps, SORA assessment tables, OSO matrix (shows "n gaps" from evidence), ERP skeleton (not started), derivation trace appendix (node count). Glyph and ink per state: `▣` accent, `◧` sail-3, `□` low.
   - **"Generate v{n+1}":** the orchestrated moment — rows tick complete in sequence as generation runs. Then `ws.addDossier` and a toast "Dossier v4 generated" with a DOWNLOAD action.
   - **"Download DOCX":** add the `docx` npm package and build it client-side:
     - cover page with the rulebase stamp
     - the disclaimer in every page header
     - ConOps summary from the inputs
     - iGRC/GRC/ARC/SAIL tables with citations
     - OSO matrix with evidence state and file names
     - trace appendix
   - **Version history** from `ws.dossiers[op]`.
   - **Preview:** the `dossier-preview` MediaSlot (3:4, 900×1200) with "Page 14 of 62" and the disclaimer.
   - **Empty state:** the `empty-dossiers` slot when there is no determination.
3. **Settings `/app/settings`** (prototype lines ~784–829):
   - **Organisation:** name, operator registration, competent authority select.
   - **Members:** 3 of 5 seats, invite button.
   - **Billing:** €249 Team, next invoice, dossiers this period.
   - **Data region:** Frankfurt/Dublin segmented control writing `ws.region`.
   - **Rulebase pinning:** radio. Changing it opens the **"Change the pinned rulebase?" modal** listing affected determinations with SAIL deltas, then writes `ws.rulebasePin`.
   - **Appearance:** dark/light via `usePrefs().setTheme`.
   - Links to `/app/states` and `/app/overlays`, and a "Reset demo workspace" action using `ws.reset()` behind a destructive confirmation.
4. **`/app/states`** (prototype ~831–884): ComputationProgress (live, with replay and a failed variant via `failAt`), empty operations, empty dossiers, error "run stopped at the airspace assessment" with ref ENG-5081, offline "Working from the last sync", and a loading table skeleton (static stepped opacity, no shimmer).
5. **`/app/overlays`** (prototype ~886–916): buttons that fire real toasts (ok/warn/fail), the rulebase modal, and the destructive "Delete this operation and its 3 dossiers?" dialog. Its confirm stays disabled until the typed name matches, and it uses the `sail-6` top rule.
6. **404 / 500:**
   - `src/app/not-found.tsx` — "404 · That page is not on the chart"
   - `src/app/error.tsx` (client) — "500 · The engine did not answer", ref box, Retry via `reset()`, Copy reference
   - Prototype lines ~1079–1095.
7. **Polish / QA:**
   - Run the app (`npm run dev`) and click through at 1440 and 390 in both themes.
   - Keyboard pass: focus rings, drawer and modal focus traps.
   - Check contrast in light theme.
   - `metadataBase` warning in `layout.tsx`.
   - An `og-default` image.
   - Wire the header search and notification buttons, or remove them.

### ▶ Next, immediately
Start with **§7.1 Intake wizard**. Read `design/project/SORA Copilot.dc.html` lines ~563–707 (the wizard markup) and the JS block at ~1258–1307 (steps, factChips, layerRows, mapStyles). Then build `src/app/app/new/page.tsx` and `src/components/wizard/*`, reusing `MapVolumeEditor.tsx`. After each feature: `npm test && npm run build`, then commit and push to `main`.

---

## 8. Conventions

- Match the existing code: Tailwind utilities from the token layer, no hard-coded colours (except `text-paper/70`-style ink on the always-black footer), and `t-*` type roles.
- Labels are written in sentence case in the source; the `t-micro` utility uppercases them.
- Panels are `bg-sheet`, side by side inside a `gap-sheet` flex or grid, with page padding `p-4 md:p-6` (app) or `px-4 md:px-12` (marketing).
- Primary button = lime, at most one per view. Secondary = hairline-strong outline. Radius is 2px in the app; marketing uses `shape="pill"`.
- Every derived number shown must come from the engine or the geometry. Never type a SAIL in by hand.
- Do not claim things the build doesn't do. Uploads keep file names only, on this device, and the UI says so.
- Keep `engine/` free of React and DOM; add a test for any engine change.

---

## 9. Kickoff check for the new session

When you are up to speed, reply to the owner in a few lines:
- confirm you know the product, the stack decisions, what's done and what's left
- state that the next task is the intake wizard
- ask whether to proceed or whether anything has changed

**Don't start coding until they say go.**
