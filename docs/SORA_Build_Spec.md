# SORA Copilot — Build Spec (MD 3 of 3)

Attach this to the Claude Code session alongside Block 2 of `SORA_01_Prompts.md`. This document is the engineering contract. Where it conflicts with `/design`, this document wins.

---

## 1. Product in one paragraph

A SaaS that automates the EU drone Specific Operations Risk Assessment. The operator describes a mission; a symbolic rules engine (Answer Set Programming, clingo) computes ground risk class, air risk class, SAIL, required Operational Safety Objectives and containment requirements, with a complete justification trace; an LLM handles only conversational intake and prose generation. Output is an authority-ready dossier.

**The invariant that defines the product: the LLM never computes a determination.** This is enforced architecturally and tested.

## 2. Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, uvicorn | |
| Rules engine | `clingo` (Python API) + `clorm` | wheels available on manylinux, installs on Render |
| Counterfactuals | `z3-solver`, with a clingo-optimisation fallback | see §7.5 |
| Geospatial | `shapely`, `pyproj`, `rasterio` (optional), PostGIS in Supabase | |
| Documents | `python-docx` for DOCX, `weasyprint` for PDF | WeasyPrint needs system libs — see Dockerfile |
| LLM | `anthropic` SDK, model `claude-sonnet-4-6` | structured output via tool-use schema |
| Database | Supabase Postgres (free tier, EU region) with PostGIS + RLS | |
| Auth | Supabase Auth (email + magic link) | backend verifies JWT |
| Storage | Supabase Storage buckets | |
| Frontend | Next.js 15 App Router, **static export**, TypeScript, Tailwind v4, shadcn/ui, Framer Motion, MapLibre GL, React Flow, TanStack Query, react-hook-form + zod | |
| Payments | Stripe Checkout + webhook | Phase 8, can be deferred |
| Hosting | Backend → Render (Docker web service, free). Frontend → Cloudflare Pages. DB → Supabase | |

**Not allowed:** Redis, Celery, RabbitMQ, any always-on worker, any paid infrastructure beyond the Anthropic API key. Background work uses FastAPI `BackgroundTasks`; scheduled work uses Supabase `pg_cron` or a Render Cron Job.

## 3. Repository structure

```
/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, routers, CORS, lifespan
│   │   ├── config.py                # pydantic-settings
│   │   ├── deps.py                  # auth dependency, db client, org scoping
│   │   ├── db/
│   │   │   ├── client.py            # supabase-py client (service role)
│   │   │   └── migrations/          # numbered .sql, applied via Supabase SQL editor or CLI
│   │   ├── domain/                  # Pydantic models — the shared vocabulary
│   │   │   ├── mission.py
│   │   │   ├── determination.py
│   │   │   ├── trace.py
│   │   │   └── oso.py
│   │   ├── engine/                  # ← PURE. no network, no LLM, no DB.
│   │   │   ├── runner.py            # facts in → Determination out
│   │   │   ├── facts.py             # Mission → ASP ground atoms
│   │   │   ├── trace.py             # clingo model → TraceNode tree
│   │   │   ├── counterfactual.py    # z3 / clingo optimisation
│   │   │   └── rulebase/
│   │   │       └── sora_2_5/
│   │   │           ├── VERSION            # e.g. 2.5.0-rc1
│   │   │           ├── CHANGELOG.md
│   │   │           ├── 00_core.lp         # types, helpers, closed-world decls
│   │   │           ├── 10_igrc.lp
│   │   │           ├── 20_mitigations.lp  # M1, M2 + robustness
│   │   │           ├── 30_arc.lp
│   │   │           ├── 40_sail.lp
│   │   │           ├── 50_oso.lp
│   │   │           ├── 60_containment.lp
│   │   │           ├── 70_sts_pdra.lp     # phase 7
│   │   │           ├── 90_national_at.lp  # Austria overrides
│   │   │           ├── 90_national_de.lp  # Germany overrides (phase 7)
│   │   │           └── tables/            # CSV source-of-truth, see §6
│   │   ├── services/
│   │   │   ├── intake.py            # wizard persistence, fact confirmation
│   │   │   ├── geo.py               # volume derivation, density classification
│   │   │   ├── determination.py     # orchestration: facts → engine → persist
│   │   │   ├── dossier.py           # DOCX/PDF render
│   │   │   └── llm.py               # ← the ONLY module importing anthropic
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── operations.py
│   │   │   │   ├── drones.py
│   │   │   │   ├── determine.py
│   │   │   │   ├── counterfactual.py
│   │   │   │   ├── geo.py
│   │   │   │   ├── dossier.py
│   │   │   │   ├── intake_chat.py
│   │   │   │   ├── public.py        # free category checker, unauthenticated
│   │   │   │   └── billing.py
│   │   └── templates/               # DOCX/HTML dossier templates
│   ├── tests/
│   │   ├── golden/                  # published SORA worked examples as fixtures
│   │   ├── test_engine_*.py
│   │   ├── test_boundary.py         # ← the LLM-isolation test, §4
│   │   └── test_api_*.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md
├── frontend/
│   ├── app/
│   │   ├── (marketing)/             # landing, pricing, checker, legal
│   │   ├── (app)/                   # dashboard, fleet, operations, settings
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                      # shadcn primitives
│   │   ├── domain/                  # SailBadge, DerivationTree, MapVolumeEditor, ...
│   │   └── media/MediaSlot.tsx
│   ├── lib/
│   │   ├── api.ts                   # typed client, generated from OpenAPI
│   │   ├── supabase.ts
│   │   └── media-manifest.ts        # ← §11
│   ├── public/media/                # you drop real assets here later
│   ├── styles/tokens.css            # copied from /design
│   ├── tailwind.config.ts
│   └── next.config.ts               # output: 'export', images.unoptimized: true
├── design/                          # READ ONLY. Approved design system + screens.
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RULEBASE.md                  # how to add/verify a rule
│   └── DEPLOY.md
├── .env.example
├── PLAN.md
└── README.md
```

## 4. The neurosymbolic boundary — enforced, not promised

Three mechanisms, all required:

1. **Import isolation.** `app/engine/**` may import only stdlib, `clingo`, `clorm`, `z3`, `pydantic`, and `app/domain/**`. It may not import `app/services/llm.py`, `anthropic`, `httpx`, `requests`, or `app/db/**`.
2. **A test that enforces it.** `tests/test_boundary.py` walks the AST of every file under `app/engine/` and fails on any forbidden import. Also assert that `app/services/llm.py` never imports `app.engine.runner` or writes to the `determinations` table.
3. **Data-flow gate.** The LLM emits `ProposedFact` objects only. A `ProposedFact` is inert: it carries `field`, `value`, `confidence`, `source_span`, `status: pending|confirmed|rejected`. The determination service reads **only** facts with `status == confirmed`. Confirmation happens by explicit user action through `POST /api/v1/operations/{id}/facts/{fact_id}/confirm`. There is no code path from a pending fact to the engine.

Document this in `docs/ARCHITECTURE.md` with the diagram. It is a selling point and an academic artefact, not just hygiene.

## 5. Domain model (Pydantic — this is the shared vocabulary)

```python
class OperationType(StrEnum): VLOS = "vlos"; EVLOS = "evlos"; BVLOS = "bvlos"

class GroundEnvironment(StrEnum):
    CONTROLLED = "controlled_ground_area"
    SPARSELY_POPULATED = "sparsely_populated"
    POPULATED = "populated"
    ASSEMBLY = "assembly_of_people"

class AirspaceClass(StrEnum): A="a"; B="b"; C="c"; D="d"; E="e"; F="f"; G="g"

class Robustness(StrEnum): NONE="none"; LOW="low"; MEDIUM="medium"; HIGH="high"

class SAIL(StrEnum): I="I"; II="II"; III="III"; IV="IV"; V="V"; VI="VI"
class ARC(StrEnum): A="a"; B="b"; C="c"; D="d"

class Drone(BaseModel):
    id: UUID; name: str
    max_dimension_m: float          # max characteristic dimension
    mtom_kg: float
    cruise_speed_ms: float
    max_speed_ms: float
    kinetic_energy_j: float | None  # computed if absent
    fitted_mitigations: list[Literal["parachute","tether","fts","daa","low_speed"]]

class OperationalVolume(BaseModel):
    flight_geography: GeoJSONPolygon
    contingency_volume: GeoJSONPolygon | None   # derived, user-adjustable
    ground_risk_buffer: GeoJSONPolygon | None   # derived, user-adjustable
    max_altitude_agl_m: float
    adjacent_area_km: float                     # derived from altitude + speed

class MitigationClaim(BaseModel):
    kind: Literal["m1_strategic","m1_ers","m2_impact","strategic_air","tactical_air"]
    robustness: Robustness
    evidence_status: Literal["none","claimed","documented","verified"]
    notes: str | None

class Mission(BaseModel):
    id: UUID; org_id: UUID; drone_id: UUID
    operation_type: OperationType
    volume: OperationalVolume
    ground_environment: GroundEnvironment
    population_density_per_km2: float | None    # from geo layer, user-confirmable
    airspace_class: AirspaceClass
    near_aerodrome: bool
    altitude_band: Literal["below_500ft","above_500ft"]
    controlled_airspace: bool
    atypical_airspace: bool
    mitigations: list[MitigationClaim]
    country: Literal["AT","DE","EU"]

class TraceNode(BaseModel):
    id: str
    conclusion: str                 # human-readable, e.g. "iGRC = 6"
    rule_id: str                    # e.g. "sora25.igrc.row3.col4"
    citation: Citation              # doc, section, page, url
    premises: list[str]             # ids of child nodes or fact ids
    kind: Literal["fact","rule","override","default"]

class OsoRequirement(BaseModel):
    oso_id: str                     # "OSO#05"
    title: str
    required_robustness: Robustness
    citation: Citation
    status: Literal["unmet","claimed","documented","verified"]

class Determination(BaseModel):
    id: UUID; operation_id: UUID
    rulebase_version: str
    igrc: int
    final_grc: int
    initial_arc: ARC
    residual_arc: ARC
    sail: SAIL | Literal["certified_category"]
    osos: list[OsoRequirement]
    containment: ContainmentRequirement
    tmpr: Literal["none","low","medium","high"]
    trace: list[TraceNode]
    warnings: list[str]
    computed_at: datetime
```

## 6. Rulebase — the part you must not improvise

### 6.1 Absolute rule

**Do not invent regulatory values.** Every number in the rulebase comes from a transcribed official source. The pipeline is: CSV table (transcribed, with a `source` column) → generated `.lp` facts → clingo rules that reason over them.

Ship each table as `backend/app/engine/rulebase/sora_2_5/tables/*.csv` with a header block naming the document, version, section and page it was transcribed from, plus a `verified: true|false` flag. A generator script `scripts/build_rulebase.py` turns CSVs into `.lp` fact files at build time and refuses to run if any row is malformed.

If a table has not yet been transcribed from the official document, keep the seed values below **and mark them UNVERIFIED everywhere** — in the CSV header, in `Determination.warnings`, and as a visible banner in the verdict UI. Tell me which file to fill in. Never silently ship a guess in a compliance product.

### 6.2 Tables required

| File | Shape | Source |
|---|---|---|
| `igrc.csv` | rows = max characteristic dimension bands (1 m / 3 m / 8 m / 20 m / 40 m), columns = population density bands (controlled ground area, <5, <50, <500, <5 000, <50 000, >50 000 ppl/km², assembly) → integer iGRC | SORA 2.5 main body, iGRC table |
| `m1_m2.csv` | mitigation kind × robustness → GRC delta, plus applicability preconditions | SORA 2.5 Annex B |
| `arc.csv` | airspace class × altitude band × environment (controlled/uncontrolled, airport/non-airport, atypical) → initial ARC | SORA 2.5 Annex C |
| `sail.csv` | final GRC × residual ARC → SAIL | SORA 2.5 main body, SAIL matrix |
| `oso.csv` | SAIL × OSO id → required robustness (None/Low/Medium/High), plus OSO title and citation | SORA 2.5 main body, OSO matrix |
| `containment.csv` | SAIL / GRC conditions → containment requirement level | SORA 2.5 containment section |
| `tmpr.csv` | residual ARC → tactical mitigation performance requirement | SORA 2.5 Annex D |

### 6.3 Seed SAIL matrix (UNVERIFIED — must be checked against SORA 2.5)

```
final GRC \ residual ARC :   a     b     c     d
        ≤ 2              :   I     II    IV    VI
          3              :   II    II    IV    VI
          4              :   III   III   IV    VI
          5              :   IV    IV    IV    VI
          6              :   V     V     V     VI
          7              :   VI    VI    VI    VI
        > 7              :   certified category — operation out of scope
```

### 6.4 ASP conventions

- Predicates, lower snake case: `fact/2`, `igrc/1`, `grc/1`, `arc_initial/1`, `arc_residual/1`, `sail/1`, `oso_required/2`, `containment/1`.
- **Every derived atom carries a justification atom.** For each rule that concludes `X`, also derive `because(X, RuleId, Premises)` in the same rule body. The trace formatter reads only `because/3`. A conclusion without a matching `because/3` is a bug — add a clingo integrity constraint that makes such a model unsatisfiable.
- Non-monotonicity is the point: national annexes and PDRA/STS shortcuts are written as defeasible overrides.

```prolog
% default → override pattern; use it consistently
grc(V) :- grc_default(V), not grc_overridden.
grc(V) :- grc_override(V, _RuleId).
grc_overridden :- grc_override(_, _).
because(grc(V), RuleId, (grc_default(V),)) :- grc(V), grc_default(V), not grc_overridden, RuleId = "sora25.grc.default".
```

- Rule ids are stable strings: `sora25.<section>.<rule>` for core, `at.<rule>` / `de.<rule>` for national, `pdra.<id>.<rule>` for shortcuts. Rule id → citation mapping lives in `tables/citations.csv`.
- Determinism: run clingo with `--models=1` for the determination path; if more than one answer set exists, that is a rulebase bug — assert on it in tests.

### 6.5 Golden tests

`tests/golden/` holds worked examples with expected iGRC / GRC / ARC / SAIL / OSO set. Sources: published SORA worked examples, EASA guidance material examples, and any case I supply. Each golden case is a JSON mission plus expected outputs plus the rulebase version it was verified against. Engine changes may not land with a failing golden case.

## 7. Services

### 7.1 `geo`
- Input: flight geography GeoJSON polygon, max altitude, drone speed.
- Derive **contingency volume** (lateral and vertical buffer from altitude, speed, GPS/position-keeping assumptions — parameters in `tables/buffers.csv`, transcribed, not invented) and **ground risk buffer** (ballistic/1:1 rule as the conservative MVP default, flagged as such).
- Derive **adjacent area** ring.
- Classify **population density**: MVP path is a coarse lookup — bundle a downsampled GHSL / Eurostat GEOSTAT 1 km raster clipped to AT + DE as a static asset, sample the maximum density within the ground risk buffer, map to the iGRC density band, and **always show the user the result for confirmation with an override**. Store the sampled value and the raster version in `geo_facts` so determinations are reproducible.
- All geometry in EPSG:4326 for storage, reprojected to a local equal-area CRS for area and buffer maths.

### 7.2 `intake`
Persists wizard state per operation. Accepts `ProposedFact` batches from the LLM, exposes confirm/reject, and emits a validated `Mission` only when every required field is confirmed. `POST /determine` returns 409 with the list of unconfirmed fields if it is not.

### 7.3 `determination`
Orchestrates: load Mission → `facts.py` renders ground atoms → `runner.py` runs clingo → `trace.py` builds the TraceNode tree → persist `Determination` with `rulebase_version` pinned → return. Idempotent per (operation_id, mission_hash, rulebase_version): re-running with identical input returns the stored determination.

### 7.4 `llm` — the only module importing `anthropic`
Three jobs, all bounded:
1. **Conversational intake** → `ProposedFact[]` via tool-use with a strict JSON schema mirroring `Mission`. Temperature 0. Never returns a conclusion field.
2. **Dossier prose** → ConOps narrative, ERP skeleton, OSO compliance narrative. Input is the Determination plus operator inputs only. System prompt states explicitly that it may not restate, contradict or recompute any risk value, and that every factual sentence must correspond to a supplied fact.
3. **Trace explanation** → plain-language explanation of a single TraceNode and its citation, grounded in a retrieved quote from the official text.

Every LLM call is logged to `llm_calls` with the prompt hash, model, token counts and latency. Hard cap per org per month, configurable, enforced before the call.

### 7.5 `counterfactual`
"What minimal change gets me to SAIL ≤ target?" Search over a bounded parameter set: max altitude, ground environment band, operation type, population density band, and the mitigation claims (kind × robustness). Approach:
- **MVP (phase 5):** bounded enumeration — for each single-parameter change in a discrete candidate list, re-run the engine and keep changes that reduce SAIL. Rank by an "effort cost" per parameter defined in `tables/cf_costs.csv`. This is fast enough for the candidate space and requires no new solver.
- **Phase 7:** Z3 optimisation over the encoded tables for genuine minimal multi-parameter change sets, with the enumeration as fallback and a cross-check test that both agree on single-parameter cases.
Each suggestion returns: the change, the resulting SAIL, the resulting OSO delta, and what evidence the new robustness level would require.

### 7.6 `dossier`
DOCX via `python-docx` from templates in `app/templates/`. Sections: cover, ConOps, operational volume description with a static map render, SORA assessment tables (iGRC → GRC → ARC → SAIL derivation), OSO compliance matrix, mitigation evidence index, ERP skeleton, and a **justification appendix** rendering the full trace with citations. Every generated file is uploaded to Supabase Storage and versioned in `dossiers`. PDF via WeasyPrint from the same content model, phase 6.

## 8. Database (Supabase)

Migrations as numbered SQL files. Enable `postgis`, `pgcrypto`.

```
orgs(id, name, country, plan, stripe_customer_id, created_at)
org_members(org_id, user_id, role)                     -- role: owner|admin|member
drones(id, org_id, name, max_dimension_m, mtom_kg, cruise_speed_ms, max_speed_ms,
       kinetic_energy_j, fitted_mitigations jsonb, created_at)
operations(id, org_id, drone_id, name, status, mission jsonb,
           flight_geography geography(Polygon,4326),
           contingency_volume geography(Polygon,4326),
           ground_risk_buffer geography(Polygon,4326),
           created_by, created_at, updated_at)
proposed_facts(id, operation_id, field, value jsonb, confidence, source_span,
               status, confirmed_by, confirmed_at)
geo_facts(id, operation_id, density_per_km2, density_band, raster_version,
          airspace_snapshot jsonb, sampled_at)
determinations(id, operation_id, rulebase_version, mission_hash, igrc, final_grc,
               initial_arc, residual_arc, sail, tmpr, containment jsonb,
               osos jsonb, trace jsonb, warnings jsonb, computed_at)
mitigations(id, operation_id, kind, robustness, evidence_status, notes)
evidence_files(id, operation_id, oso_id, mitigation_id, storage_path, filename,
               uploaded_by, uploaded_at)
dossiers(id, operation_id, determination_id, version, storage_path, format,
         generated_at)
rulebase_versions(version, released_at, changelog, sources jsonb, is_current)
impact_alerts(id, org_id, operation_id, from_version, to_version, severity,
              summary, created_at, acknowledged_at)      -- phase 7
llm_calls(id, org_id, purpose, model, prompt_hash, input_tokens, output_tokens,
          latency_ms, created_at)
```

**RLS on every table.** Policy pattern: a row is visible if `org_id` is in `select org_id from org_members where user_id = auth.uid()`. The backend uses the service-role key and applies org scoping in `deps.py` — never trust an `org_id` from the request body; derive it from the JWT.

Storage buckets: `evidence` (private), `dossiers` (private, signed URLs, 15-minute expiry), `public-assets`.

## 9. API surface (`/api/v1`)

```
POST   /auth/session                     exchange Supabase JWT → org context
GET    /orgs/me
GET    /drones                           POST /drones   PATCH /drones/{id}   DELETE
GET    /operations                       POST /operations
GET    /operations/{id}                  PATCH /operations/{id}   DELETE
POST   /operations/{id}/geo/derive       → contingency, buffer, adjacent area, density
POST   /operations/{id}/intake/chat      → ProposedFact[] (SSE stream)
POST   /operations/{id}/facts/{fid}/confirm | /reject
POST   /operations/{id}/determine        → Determination (409 if unconfirmed facts)
GET    /operations/{id}/determination    → latest
POST   /operations/{id}/counterfactual   body {target_sail} → Suggestion[]
POST   /operations/{id}/counterfactual/apply
GET    /operations/{id}/osos             POST /operations/{id}/osos/{oso}/evidence
POST   /operations/{id}/dossier          → job id; GET /dossiers/{id} → signed URL
GET    /rulebase/current                 version, changelog, source list
POST   /public/category-check            unauthenticated, rate-limited — free checker
POST   /billing/checkout                 POST /billing/webhook
GET    /healthz
```

FastAPI emits OpenAPI; generate the frontend client from it (`openapi-typescript`) so types never drift. Errors follow RFC 7807 problem+json with a machine-readable `code`.

## 10. Frontend rules

- `next.config.ts`: `output: 'export'`, `images: { unoptimized: true }`, `trailingSlash: true`. No server components that fetch, no server actions, no route handlers — Cloudflare Pages serves static files only.
- Auth in the browser via `@supabase/supabase-js`; the access token goes to the backend as a Bearer header. `NEXT_PUBLIC_API_URL` points at Render.
- Data layer: TanStack Query, one hook per endpoint, generated types.
- Tokens: copy `/design/tokens.css` into `frontend/styles/tokens.css` and `/design/tailwind.theme.ts` into the Tailwind config. Do not re-derive the palette.
- Build components from `/design/components.md` and the screenshots. Match spacing, weights and motion presets; do not "improve" the design silently. If something is genuinely unimplementable, tell me rather than substituting.
- The derivation tree uses React Flow with a `dagre` layout; nodes are collapsible; every node shows its citation chip; a "copy trace" action emits the whole tree as markdown.
- The map uses MapLibre GL with a free raster/vector basemap style that requires no key, three drawing layers, and area readouts in m².
- `prefers-reduced-motion` is honoured globally via a motion provider that swaps Framer presets for instant transitions.

## 11. Media handling — so you never touch code when I add assets

`frontend/lib/media-manifest.ts` is the single registry, generated from `/design/media-manifest.md`:

```ts
export const MEDIA = {
  'hero-loop':   { kind:'video', src:'/media/hero-loop.mp4', poster:'/media/hero-poster.jpg',
                   w:1920, h:1080, alt:'Drawing an operational volume and resolving a SAIL' },
  'feature-trace': { kind:'image', src:'/media/feature-trace.png', w:1600, h:1200, alt:'…' },
  // …one entry per slot in the design manifest
} as const;
```

`<MediaSlot id="hero-loop" />` reserves the aspect ratio from `w`/`h`, renders the designed placeholder when the file is missing (probe with `onError`), lazy-loads below the fold, and in `NODE_ENV === 'development'` overlays the slot id and required dimensions. Videos are `muted playsInline loop autoPlay preload="metadata"` and fall back to the poster under reduced motion.

When I drop files into `frontend/public/media/` with the manifest filenames, they appear. No code change.

## 12. Build phases — stop and check at every boundary

**Phase 1 — Skeleton.** Repo structure, FastAPI app with `/healthz`, Next.js static-export shell with tokens wired and the theme switch working, Supabase project + auth + migrations 001, Docker build succeeds locally, README with run instructions.
*DoD:* `docker build` passes; both sides run with one command each; I can sign up and land on an empty dashboard.

**Phase 2 — Engine v1 (no web).** The whole SORA chain in clingo: iGRC → M1/M2 → GRC → ARC → residual ARC → SAIL → OSO expansion → containment. `because/3` on every conclusion. Trace formatter. CSV→LP generator. CLI: `python -m app.engine.cli mission.json`. Golden tests.
*DoD:* every golden case passes; every determination has a complete trace with citations; `test_boundary.py` passes; UNVERIFIED tables are listed for me by filename.

**Phase 3 — Data + API.** Migrations complete, RLS policies, org scoping, CRUD for drones and operations, `/determine` wired to the engine, OpenAPI generated, typed frontend client generated.
*DoD:* I can create a drone and an operation over the API and get a persisted determination with the rulebase version pinned.

**Phase 4 — Geo + intake wizard.** Volume derivation, density classification with user confirmation, the full wizard UI including the map step, fact confirmation UI.
*DoD:* I can draw a polygon, get derived volumes and a density band, complete the wizard, and hit determine from the UI.

**Phase 5 — Verdict + counterfactuals.** Verdict screen, derivation tree, OSO matrix with gap analysis, counterfactual advisor (enumeration) with apply-and-rerun.
*DoD:* the verdict screen matches `/design/screens/verdict.html`; suggestions genuinely lower SAIL when applied.

**Phase 6 — Dossier + conversational intake.** DOCX export with the justification appendix, evidence upload, LLM intake panel producing confirmable facts, LLM prose for ConOps/ERP.
*DoD:* a downloadable DOCX where every risk value matches the stored determination exactly; the boundary test still passes.

**Phase 7 — Marketing site + free checker + Austria pack.** Landing, pricing, legal, the public category checker, Austro Control process notes and forms checklist, Germany overrides if time allows.
*DoD:* the marketing site matches the design with placeholder media; the checker works unauthenticated and rate-limits.

**Phase 8 — Billing + deploy.** Stripe Checkout and webhook, plan gating, Render deploy, Cloudflare Pages deploy, environment docs, smoke test against production.
*DoD:* a live URL where a new user can sign up, run a determination, and be blocked at the correct plan limit.

## 13. Environment

```
# backend
SUPABASE_URL=                 SUPABASE_SERVICE_ROLE_KEY=      SUPABASE_JWT_SECRET=
ANTHROPIC_API_KEY=            ANTHROPIC_MODEL=claude-sonnet-4-6
STRIPE_SECRET_KEY=            STRIPE_WEBHOOK_SECRET=
RULEBASE_VERSION=2.5.0-rc1    CORS_ORIGINS=http://localhost:3000,https://…pages.dev
LLM_MONTHLY_CALL_CAP=500      ENV=development
# frontend
NEXT_PUBLIC_SUPABASE_URL=     NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=          NEXT_PUBLIC_MAP_STYLE_URL=
```

## 14. Deployment notes

- **Render free web service** sleeps after 15 minutes idle; cold start is slow. The frontend must show a warming state rather than an error on the first call, and `/healthz` is pinged by an external free uptime monitor.
- **Dockerfile** must install WeasyPrint's system dependencies (`libcairo2`, `libpango-1.0-0`, `libpangocairo-1.0-0`, `libgdk-pixbuf-2.0-0`, `libffi-dev`, `shared-mime-info`). Multi-stage; final image slim.
- **Supabase free tier** pauses a project after ~7 days of inactivity — document how to resume it.
- **Cloudflare Pages:** build command `npm run build`, output directory `out`.
- EU regions everywhere (Supabase EU, Render Frankfurt) — data residency is a stated selling point.

## 15. Non-negotiables recap

1. LLM never determines. Tested, not promised.
2. Every conclusion has a trace, a citation and a pinned rulebase version.
3. No invented regulatory values; UNVERIFIED is surfaced to the user.
4. Engine changes ship with passing golden tests.
5. Free tier only.
6. `/design` is the visual authority; this document is the engineering authority.
