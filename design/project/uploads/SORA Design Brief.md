# SORA Copilot — Design Brief (MD 2 of 3)

Attach this to the Claude Design session alongside Block 1 of `SORA_01_Prompts.md`.

---

## 1. What the product actually is

A European drone operator cannot legally fly anything serious — beyond visual line of sight, over a town, above a crowd, near an airport — without first handing the national aviation authority a **SORA**: a formal risk assessment proving the flight is survivable for everyone underneath it and everything around it.

Producing that assessment today means paying an aviation consultant €1,000–5,000 and waiting weeks. SORA Copilot replaces that: the operator describes the mission, a rules engine computes the official risk chain, and the app emits an authority-ready dossier with every conclusion traced back to the regulation that produced it.

The chain the product computes, in the operator's own vocabulary:

```
drone size + what's underneath  →  iGRC  (intrinsic ground risk class, 1-10)
        + mitigations M1/M2     →  GRC   (final ground risk class)
airspace + altitude + traffic   →  ARC   (air risk class, a / b / c / d)
        + strategic mitigation  →  residual ARC
GRC × residual ARC              →  SAIL  (I, II, III, IV, V, VI)
SAIL                            →  ~24 OSOs at Low / Medium / High robustness
                                +  containment requirements
```

Use these terms. Never soften them into "risk score" or "safety level". The operator already speaks this language; meeting them in it is the first proof that the tool is real.

## 2. Who is looking at this

- **A two-person inspection company in Graz.** Currently declines jobs it could legally take because the paperwork is unaffordable. Non-technical, deeply practical, allergic to being sold to.
- **A solo BVLOS operator.** Wants one answer fast: *can I fly this, and if not, what would it take.*
- **A compliance officer at a drone consultancy.** Will personally be embarrassed in front of Austro Control if this tool is wrong. Scrutinises the trace before they trust the verdict.
- **Eventually, an authority case officer** reading a dossier this app produced. The output has to look like it came from an aviation professional.

None of them are impressed by gradients. All of them are impressed by being shown the working.

## 3. Positioning and voice

**Positioning:** decision-support, not authority. The NAA grants the authorisation; this tool prepares and verifies the assessment. That humility is load-bearing legally and it should be visible in the interface, not buried in a footer.

**Voice:** the pre-flight checklist. Precise, calm, declarative, faintly clipped. Never enthusiastic, never apologetic.

Fixed strings — use these verbatim:
- Product name: **SORA Copilot**
- Primary promise: **From mission to dossier in minutes.**
- Audit promise: **Every line cites its rule.**
- Disclaimer, shown on the verdict screen and in every export: *SORA Copilot prepares and verifies your risk assessment. Your national aviation authority grants the authorisation.*
- Rulebase stamp, shown on every determination: *Rulebase {version} · {date}*

Words to avoid entirely: effortless, seamless, magic, AI-powered, revolutionise, unlock, empower, game-changing, supercharge.

## 4. Visual direction

The subject matter is **instrumentation** — flight decks, airspace charts, ED-269 geo-zone overlays, checklists, hazard bands. Not "aviation" as in stock photos of sunsets over runways. Aviation as in *a panel that tells you the truth under pressure*.

**Direction to pursue:** dark-first, high-contrast, instrument-panel discipline. Thin precise lines. Data set in a face with real numerals. Colour used almost exclusively to encode risk — so that when colour appears, it means something. Large areas of quiet, then one dense, information-rich object (the derivation tree, the map, the SAIL badge) carrying the whole screen.

**What to avoid, because it is where this brief would drift by default:**
- The near-black-plus-one-acid-accent SaaS dashboard. If you go dark, earn it with more than one ink level and a real material logic.
- Identical rounded cards in a 3-column grid for everything regardless of content weight.
- Tracked-out ALL-CAPS eyebrow labels over every section heading.
- A monospace face used decoratively on things that are not data.
- Glassmorphism, aurora blobs, and floating 3D drones.
- Terracotta/warm-clay accents on cream. Wrong century, wrong industry.

**Colour, as direction not prescription:** you need a neutral ink ramp deep enough to build a panel out of (at least four steps), one signal colour for interactive affordance, and a six-step risk ramp for SAIL I→VI that reads correctly for colour-blind users and in greyscale. The risk ramp is the most important palette decision in the product — design it first and let the rest of the palette stay out of its way.

**Typography:** one or two Google Fonts. Requirements: tabular lining numerals, a genuine range of weights, and legibility at 11–13px for dense tables. If you use a second family for data and traces, it must be doing work, not signalling technicality.

**Motion:** one orchestrated moment per screen, maximum.
- On the **verdict screen**, the derivation tree drawing itself edge by edge as the reasoning resolves is the single showiest moment in the product. Earn it: it should feel like a computation completing, not a decoration animating.
- Everywhere else, motion answers an action — a panel expanding, a volume extruding on the map, a counterfactual being applied and the SAIL badge stepping down.
- Numbers may count up **once**, on the verdict. Never again.
- `prefers-reduced-motion` collapses all of this to instant state changes with no loss of information.

## 5. Media plan

I will add real media myself after the build. Design the slots; design the placeholder states so they look deliberate.

Slots I know I need — add any others the design calls for:

| id | Page | Type | Ratio | What it will show |
|---|---|---|---|---|
| `hero-loop` | Landing | video (muted, autoplay, loop) | 16:9 | Screen capture: an operational volume being drawn on a map, then the SAIL badge resolving |
| `hero-poster` | Landing | image | 16:9 | First frame of the above, for the video poster and reduced-motion fallback |
| `feature-trace` | Landing | image | 4:3 | The derivation tree, full width, legible |
| `feature-map` | Landing | image | 4:3 | Map with flight geography, contingency volume, ground risk buffer |
| `feature-dossier` | Landing | image | 3:4 | A page of the exported DOCX dossier |
| `feature-counterfactual` | Landing | video | 1:1 | A parameter changing and SAIL stepping III → II |
| `proof-logos` | Landing | image strip | — | Authority / standards marks (EASA, Austro Control, LBA) — reference only, no endorsement implied |
| `persona-{1,2,3}` | Landing | image | 1:1 | Operator portraits for the persona section |
| `og-default` | Meta | image | 1200×630 | Social card |
| `empty-operations` | App | illustration | 1:1 | Empty state, operations list |
| `empty-dossiers` | App | illustration | 1:1 | Empty state, dossiers list |

For each slot the placeholder must carry: the correct aspect ratio reserved (no layout shift when the real asset lands), a designed fill consistent with the system, and the slot id visible in dev mode only.

## 6. Screens to produce

### Marketing site (public)
1. **Landing.** Hero, the risk-chain explainer (this is the hero's real job — show the chain, not a testimonial), the four capability sections keyed to the media slots above, pricing, FAQ, footer with the disclaimer.
2. **Pricing.** Free / Pro / Team / Consultancy / one-off per-dossier. Free tier is the category checker.
3. **Free category checker.** A three-question public tool: is this flight open, specific, or certified category, with an estimated SAIL. No account. This is the top of the funnel and should feel like a real instrument, not a lead-gen form.
4. **Legal.** Terms, privacy, the disclaimer in full, rulebase changelog.

### Product (authenticated)
5. **Sign in / sign up.** Email and magic link.
6. **Operations dashboard.** List of the operator's missions with SAIL badge, status (draft / determined / dossier ready / submitted / authorised), rulebase version, last run. Empty state matters — most users arrive here with nothing.
7. **Drone fleet.** Aircraft records: max characteristic dimension, MTOM, cruise and max speed, kinetic energy, fitted mitigations (parachute, tether, FTS, DAA).
8. **Intake wizard.** The core flow, multi-step, resumable:
   - Aircraft selection
   - Operation type (VLOS / EVLOS / BVLOS), altitude, duration
   - **Map step** — draw flight geography, then the app derives contingency volume and ground risk buffer; user adjusts. This screen is half the product's credibility. Design it properly: layer control, area readout, population density overlay, adjacent-area indication.
   - Ground environment: controlled ground area / sparsely populated / populated / assembly of people
   - Airspace: class, altitude band, aerodrome proximity, geo-zones
   - Mitigations claimed, with robustness level and evidence status per mitigation
   - Review and confirm — every fact the LLM extracted from conversation shows here for explicit confirmation before it reaches the engine
9. **Verdict.** The product's centrepiece:
   - SAIL badge, large, with the risk ramp
   - The chain as a horizontal readout: iGRC → GRC → ARC → residual ARC → SAIL
   - **Derivation tree** — expandable nodes, each node showing the rule that fired and its regulation citation, with the raw fact leaves at the bottom
   - **Gap analysis** — OSOs required vs. evidenced, grouped by robustness level
   - **Counterfactual advisor** — "lower altitude to 90 m" / "add a parachute at medium robustness" → shows resulting SAIL, one click to apply and re-run
   - Rulebase stamp and disclaimer
10. **OSO detail drawer.** One OSO: what it is, required robustness, what evidence satisfies it, current status, upload evidence.
11. **Dossier builder.** Section checklist (ConOps, SORA assessment tables, OSO matrix, ERP skeleton), preview, generate, version history, download.
12. **Conversational intake panel.** A side panel present in the wizard where the operator can describe the mission in prose; extracted facts appear as confirmable chips, never as conclusions. Design the *confirmation* interaction carefully — it is the visible boundary between the LLM and the engine, and that boundary is the brand.
13. **Settings.** Organisation, members, billing, data region, rulebase version pinning.

### System
14. Loading, empty, error, and offline states for every data surface. The engine can take a few seconds — design the waiting state as a computation in progress with visible stages, not a spinner.
15. Toasts, modals, confirmation dialogs.
16. 404 and 500.

## 7. Component inventory to define

`SailBadge` (I–VI, three sizes) · `RiskChainReadout` · `DerivationTree` + `DerivationNode` · `CitationChip` · `RobustnessPill` (Low/Medium/High) · `OsoRow` + `OsoMatrix` · `MitigationCard` · `CounterfactualCard` · `MapVolumeEditor` (flight geography / contingency / buffer layers) · `DensityLegend` · `FactChip` (unconfirmed / confirmed / rejected) · `WizardStepper` · `StatusPill` · `RulebaseStamp` · `DisclaimerBanner` · `MediaSlot` · `EvidenceUploader` · `DossierSectionRow` · `EmptyState` · `ComputationProgress`.

For each: variants, all interaction states, and the props an engineer needs.

## 8. Technical constraints the design must respect

- Implementation is **Next.js 15 App Router, static export**, Tailwind CSS v4, shadcn/ui as the primitive layer, Framer Motion for motion, MapLibre GL for the map, React Flow for the derivation tree, Recharts if a chart is needed.
- Static export means: no server-side rendering, no server actions, no Next.js image optimisation. Design accordingly — assets are served as-is, so specify exact intrinsic sizes and keep the hero video small enough to be sane over a cold connection.
- Tokens must land as CSS custom properties **and** a `tailwind.config.ts` theme extension that agree with each other exactly.
- Dark is primary, light is derived. Both must be complete; the theme switch is a `data-theme` attribute on `<html>`.
- Mobile: the map step and the derivation tree need genuine mobile treatments, not a "best viewed on desktop" message. An operator checks a verdict on a phone, in a field.
- Target: LCP under 2.5s on the landing page with media present, and the app shell interactive in under 1s.

## 9. What success looks like

A compliance officer opens the verdict screen, expands three nodes of the derivation tree, finds the regulation citation on each, and stops being suspicious. Everything in the design serves that moment.
