# SORA Copilot — Build Plan

**Status: all eight phases implemented.** See §10 for the phase-by-phase state and how
each Definition of Done was checked.

What remains is not code. No regulatory table has been verified against its published
source (§8), and no national annex has been transcribed — the engine's
`90_national_*.lp` files deliberately assert nothing, and the country packs under
`backend/app/national/packs/` are marked UNVERIFIED item by item. Until you supply those
documents the product is a working engine with honest labels on it, which is the right
state to be in, but not something an operator should file with an authority.

---

## 0. Decisions taken (answered 15 Oct 2026)

| Question | Answer | Effect |
|---|---|---|
| §5.1 Map | **MapLibre GL, keep the SVG renderer for the dossier** | Wizard map becomes MapLibre with a keyless basemap and the designed layers as style layers. `MapVolumeEditor`'s SVG renderer is retained as the static map render for the DOCX. Needs `NEXT_PUBLIC_MAP_STYLE_URL`. Phase 4. |
| §5.2 Derivation tree | **React Flow + dagre, rebuild the motion** | Custom node/edge components reproduce the design's node anatomy and the `edge-draw` / `node-settle` timings; the existing mobile outline stays as the `<480px` treatment. The hand-laid SVG tree is replaced. Phase 5. |
| §6.3 Altitude threshold | **500 ft = 152.4 m, correct the UI copy** | Engine keys ARC on 500 ft AGL. Approved design text "above 150 m AGL" is relabelled "above 500 ft (152 m)" wherever it appears. Signed off as a deliberate edit to design copy. |
| §6.5 Interim SAIL in the UI | **Keep the checker and verdict working, labelled** | Both kept computing client-side through phases 1–6 behind a "preliminary estimate — computed in your browser, not a determination" label. **Done:** the verdict cut over at Phase 3, the checker at Phase 7, and `frontend/src/engine/` was deleted with the labels in the same commit. Nothing in the UI computes a risk value any more. |

Proceeding on my stated recommendations, reversible on request: **Tailwind v4 CSS-first**
(§5.3), **`ANTHROPIC_MODEL=claude-sonnet-5-5`** as the env default (§7.3), **raw clingo
API rather than clorm** (§4.1), **`frontend/src/`** rather than the spec's literal
`frontend/app/` (§4.9).

Resolved since: the `igrc.csv` speed column is kept (§6.1), `assembly` is modelled
(§6.2), the density raster is replaced by operator-entered density with a confirmable
environment hint (§7.5), and the per-tier plan limits are set in
`backend/app/services/plans.py` (§6.8 — see §10, phase 8).

**Still open, and now the only things standing between this and a usable compliance
product:** the Supabase project (§7.1), the official SORA 2.5 tables (§7.4, §8), and the
Austrian annex plus Austro Control's published process (§8).

Two governing documents:

- **SORA Build Spec** — engineering contract. Wins on architecture, data, API,
  correctness. Currently an attachment; Phase 1 commits it to `docs/SORA_Build_Spec.md`
  so the contract lives in the repo.
- `design/` — approved design system and screens. Wins on appearance, copy, spacing, motion.
  **Read-only.** Where the two conflict the spec wins; every conflict I found is in §5.

---

## 1. What exists today, and what happens to it

`main` currently holds a **single-process Next.js app at the repo root** with a
TypeScript SORA engine. It builds (17 static pages) and 9 engine tests pass. It was
built from `design/` before the build spec existed, so it predates the backend
architecture entirely.

| What is there now | Fate |
|---|---|
| `src/app/**` — marketing, checker, legal, signin, app shell, dashboard, fleet, verdict | Moves to `frontend/`. Kept; rewired to the API in phases 3–7. |
| `src/components/**` — Brand, SailBadge, MediaSlot, Toast, ui/*, verdict/*, wizard/MapVolumeEditor | Moves to `frontend/`. Kept. `MapVolumeEditor` and `DerivationTree` are affected by §5.1/§5.2. |
| `src/engine/{engine,rulebase,checker,types}.ts` — the TypeScript SORA engine | **Retired.** Phase 3 deletes it once `POST /determine` lands. It is a second rules engine, and the product's invariant is that clingo is the only one. |
| `src/engine/geometry.ts` — buffers, areas, density analysis | **Moves to the backend** (`services/geo.py`, shapely/pyproj) in Phase 4. A thin client copy survives only for drag-time preview; the committed geometry is always the server's. |
| `src/engine/engine.test.ts` — 9 tests | Becomes the seed for `backend/tests/golden/` in Phase 2. The fixture SAILs are a useful regression net against the clingo port. |
| `src/data/{fixtures,map,oso,marketing}.ts` — demo workspace | `marketing.ts` stays. `fixtures.ts`/`map.ts` become a backend demo-seed script; the app dashboard goes empty in Phase 1 per the Phase 1 DoD. |
| `src/lib/workspace.tsx` — localStorage persistence | **Retired** in Phase 3, replaced by TanStack Query against the API. |
| `HANDOFF.md` (root) | Moves to `docs/HANDOFF-design-phase.md`. Root is restricted to the spec's list. |
| `design/` | Untouched, read-only. |

Nothing above is deleted in Phase 1 except where the Phase 1 DoD requires it; the
retirements are scheduled so that no phase ends with a broken build.

---

## 2. Target repo shape (spec §3)

Root holds exactly: `backend/ frontend/ design/ docs/ README.md PLAN.md .env.example .gitignore`

---

## 3. Phase 1 — file-by-file

**Phase 1 DoD (spec §12):** `docker build` passes; both sides run with one command
each; sign up and land on an empty dashboard.

### 3.1 Root

| File | Action |
|---|---|
| `README.md` | Rewrite: prerequisites, `.env` setup, one command per side (`cd backend && make dev` / `cd frontend && npm run dev`), Supabase project setup + how to resume a paused free project, how to apply migration 001. |
| `.env.example` | All keys from spec §13, split backend/frontend, each commented with where to get it. |
| `.gitignore` | Add `__pycache__/ .venv/ *.pyc .pytest_cache/ .env .env.local frontend/out frontend/.next backend/app/engine/rulebase/**/generated/`. |
| `PLAN.md` | This file; updated at each phase boundary. |

Moves: `src/ package.json package-lock.json next.config.ts tsconfig.json postcss.config.mjs next-env.d.ts` → `frontend/`. `HANDOFF.md` → `docs/HANDOFF-design-phase.md`. The attached build spec → `docs/SORA_Build_Spec.md` so it lives in the repo. All via `git mv`.

### 3.2 `backend/`

| File | Contents |
|---|---|
| `pyproject.toml` | `requires-python = ">=3.12"`. Runtime: fastapi, uvicorn[standard], pydantic, pydantic-settings, python-multipart, pyjwt[crypto], supabase, clingo, shapely, pyproj, python-docx, weasyprint, anthropic. Dev: pytest, pytest-asyncio, httpx, ruff, mypy. Pinned minors. |
| `Makefile` | `dev`, `test`, `lint`, `fmt`, `rulebase` (CSV→LP), `docker` — so "one command per side" is literal. |
| `Dockerfile` | Multi-stage on `python:3.12-slim`. Builder installs wheels into a venv; final stage copies the venv and adds WeasyPrint runtime libs (`libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi8 shared-mime-info fonts-dejavu-core`). Non-root user, `EXPOSE 8000`, `HEALTHCHECK` on `/healthz`, `CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT`. |
| `.dockerignore` | tests, `.venv`, caches. |
| `app/main.py` | FastAPI app, CORS from `CORS_ORIGINS`, RFC 7807 exception handlers (`problem+json` with machine-readable `code`), lifespan, `/healthz` returning `{status, rulebase_version, env, git_sha}`, `include_router(v1)`. |
| `app/config.py` | `pydantic-settings` `Settings`; every spec §13 key; fails loudly on a missing required key in `ENV=production`, warns and runs degraded in development so Phase 1 is runnable before Supabase exists. |
| `app/deps.py` | `get_current_user` — verify Supabase JWT (HS256 via `SUPABASE_JWT_SECRET`), extract `sub`; `get_org_context` — resolve org from `org_members` by `user_id`, **never** from the request body; `get_db`. |
| `app/db/client.py` | Lazily-constructed `supabase` client with the service-role key. |
| `app/db/migrations/001_init.sql` | `postgis`, `pgcrypto`; every table in spec §8; indexes; `updated_at` triggers; RLS enabled on all tables with the `org_members` policy pattern; the three storage buckets; a trigger that creates an org + owner membership on first sign-in. |
| `app/db/migrations/README.md` | How to apply (Supabase SQL editor or CLI), and that migrations are numbered and never edited after being applied. |
| `app/domain/{mission,determination,trace,oso}.py` | Spec §5 verbatim, as Pydantic v2. `Citation`, `ContainmentRequirement`, `ProposedFact`, `GeoJSONPolygon` included. This is the shared vocabulary; the OpenAPI schema and the frontend types both derive from it. |
| `app/engine/__init__.py` + package dirs | Skeleton only — `runner.py`, `facts.py`, `trace.py`, `counterfactual.py` exist with module docstrings stating the import restriction and `raise NotImplementedError`. **No stubbed logic that could be mistaken for working.** Filled in Phase 2. |
| `app/engine/rulebase/sora_2_5/VERSION` | `2.5.0-rc1` |
| `app/engine/rulebase/sora_2_5/CHANGELOG.md` | Seeded; one entry per rulebase change from here on. |
| `app/engine/rulebase/sora_2_5/tables/*.csv` | **Phase 1 creates the files with their source header blocks, `verified: false`, and the seed values** (from the spec §6.3 matrix and the current TypeScript rulebase, which already carries SORA 2.5 shapes). Listed for you in §8. |
| `app/api/v1/__init__.py` | Router aggregation. |
| `app/api/v1/health.py` | `/healthz`. |
| `app/services/llm.py` | Phase 1: module docstring declaring it the **only** module permitted to import `anthropic`, plus the cap-check helper signature. No calls yet. |
| `tests/test_boundary.py` | **The neurosymbolic boundary test, in Phase 1, not Phase 2.** Walks the AST of every file under `app/engine/` and fails on any import outside {stdlib, clingo, clorm, z3, pydantic, app.domain}. Asserts `app/services/llm.py` imports neither `app.engine.runner` nor any `app.db` module, and contains no write to `determinations`. Asserts `anthropic` is imported nowhere but `app/services/llm.py`. It guards from the first commit rather than the second phase. |
| `tests/test_health.py` | `/healthz` 200 and shape. |
| `tests/conftest.py` | App fixture with settings overridden so tests need no Supabase. |
| `README.md` | Backend-local run, test and Docker instructions. |

### 3.3 `frontend/`

| File | Action |
|---|---|
| `package.json` | Add `@tanstack/react-query`, `@supabase/supabase-js`, `react-hook-form`, `zod`; dev `openapi-typescript`. MapLibre / React Flow / dagre added at the phase that needs them (see §5.1, §5.2) — not Phase 1. TypeScript stays pinned `5.9.x` (TS 7 breaks `next build`). |
| `lib/supabase.ts` | Browser client from `NEXT_PUBLIC_*`; typed session helpers. |
| `lib/auth.tsx` | `AuthProvider` — session, `signInWithOtp`, password sign-in, sign-out, `useSession()`. |
| `lib/api.ts` | `fetch` wrapper: `NEXT_PUBLIC_API_URL`, Bearer from the Supabase session, RFC 7807 parsing into a typed `ApiError`, and a **cold-start warming state** (Render free sleeps ~15 min — first call retries with backoff and surfaces "warming", never an error; spec §14). Hand-written in Phase 1; types replaced by the generated client in Phase 3. |
| `lib/query.tsx` | `QueryClientProvider`. |
| `lib/media-manifest.ts` | Spec §11 registry, one entry per slot in `design/project/media-manifest.md` (15 slots). Done now because it is structural. |
| `components/MediaSlot.tsx` | Refactor to take `id` and read the manifest; keep the existing designed placeholder, crop marks, graticule, dev-mode slot id; add `onError` probing and the reduced-motion poster fallback. |
| `app/app/**` (guard) | Client-side auth guard: unauthenticated → `/signin`. Dashboard renders the **empty state** (`empty-operations` slot) instead of fixtures, per the Phase 1 DoD. |
| `app/(auth)/signin` | Rewire the existing form to real Supabase Auth (magic link + password), with the sent/error states the design already specifies. |
| `styles/tokens.css` | Verify byte-identical to `design/project/tokens.css` apart from the documented `--font-*` substitutions; theme switch already works via `lib/prefs.tsx` + `data-theme` on `<html>`. |
| `next.config.ts` | Already `output: 'export'`, `trailingSlash: true`, `images.unoptimized`. Unchanged. |

### 3.4 `docs/`

| File | Contents |
|---|---|
| `ARCHITECTURE.md` | The neurosymbolic boundary with the diagram, the three enforcement mechanisms, and how `test_boundary.py` implements them. The selling point, written down. |
| `RULEBASE.md` | How a rule is added or verified: transcribe CSV → `build_rulebase.py` → `.lp` → golden test → CHANGELOG → VERSION bump. Includes the UNVERIFIED protocol. |
| `DEPLOY.md` | Render (Docker, Frankfurt, free-tier sleep + external uptime ping), Cloudflare Pages (`npm run build`, output `out`), Supabase (EU region, resuming a paused project), environment matrix. |
| `SORA_Build_Spec.md` | The attached spec, committed so the contract lives in the repo. |
| `HANDOFF-design-phase.md` | The old root `HANDOFF.md`. |

### 3.5 Phase 1 exit checks I will run and show you

`cd backend && pytest` (boundary + health) · `ruff check` · `mypy app` ·
`docker build` (see §7.2) · `cd frontend && npm run build` (static export, page count) ·
`npm run lint` · a manual sign-up → empty dashboard walkthrough in both themes.

---

## 4. Decisions I am making (the spec left these open)

1. **Raw clingo Python API, not clorm.** Spec §2 lists `clingo + clorm`. clorm 1.6.3
   installs fine, but it buys ORM-style fact classes we do not need — Pydantic already
   owns the typed layer, and `facts.py`/`trace.py` only need to emit and read ground
   atoms. Fewer dependencies in the one module that must stay pure. Easy to reverse;
   say so if you want clorm.
2. **Python 3.12 in Docker, `>=3.12` in `pyproject`.** The dev container here is 3.13;
   clingo, z3 and supabase all have 3.13 wheels, so both work. Production pins 3.12 per spec.
3. **Dossier generation is synchronous.** Spec §9 shapes it as `POST /dossier → job id`.
   On a Render free instance that sleeps, a `BackgroundTasks` job can be killed
   mid-flight and silently lost. A single-operation DOCX renders in ~1–3 s, so I will
   generate inline and return the signed URL, while keeping the `{job_id, status}`
   response shape so an async path can land later without an API break.
4. **RLS is defence-in-depth, not the gate.** The backend uses the service-role key,
   which bypasses RLS by design. The real authorisation boundary is `deps.py` org
   scoping from the JWT. RLS still goes on every table so that any future direct
   browser access is safe. Documented in `ARCHITECTURE.md` so nobody mistakes which
   one is load-bearing.
5. **`/healthz` is cheap and dependency-free.** It must answer while Supabase is paused
   or the uptime ping that keeps Render awake becomes a false alarm. Database
   reachability goes in a separate `/healthz/deep`.
6. **Boundary test lands in Phase 1.** Spec puts it in the Phase 2 DoD. It costs little
   and the invariant should be enforced from the first backend commit.
7. **Error envelope.** RFC 7807 `problem+json` with `code`, `title`, `detail`,
   `status`, plus `errors[]` for field-level validation and `unconfirmed_fields[]` on
   the 409 from `/determine` (spec §7.2).
8. **Idempotency key** for determinations is `sha256` over the canonical JSON of the
   confirmed `Mission` plus `rulebase_version` — stored as `mission_hash` (spec §7.3).
9. **`frontend/src/`, not `frontend/app/`.** Spec §3's tree shows `frontend/app/...`
   with no `src/`. The existing code is `src/`-based with `@/*  → ./src/*`; Next.js
   supports both identically and the alias hides the difference. Keeping `src/` avoids
   touching every import for no functional gain. Overrule me if you want the literal tree.
10. **Demo fixtures become a backend seed.** `scripts/seed_demo.py` can load the
    Steiermark Inspect workspace into a real org, so there is something to click
    through without hand-entering six operations. Opt-in, never automatic.

---

## 5. Conflicts between the build spec and `/design` — flagged, spec applied

Per your rule the spec wins. These four are the ones where that costs something real,
so I want your call before I spend the work.

### 5.1 Map: MapLibre GL vs the designed in-page SVG chart

- **Spec §10:** "The map uses MapLibre GL with a free raster/vector basemap style that
  requires no key, three drawing layers, and area readouts in m²."
- **Design:** in `design/chats/chat1.md` you explicitly chose "Designed vector chart
  surface drawn in-page — no tiles, no network, full control of the ED-269 / density /
  volume layers". `design-plan.md` §6 records it, and the previous session's handoff
  recorded "no MapLibre for now". `components/wizard/MapVolumeEditor.tsx` already
  implements it: graticule, hatched density cells, geo-zones, three extruding volume
  outlines, draggable vertices, pan/zoom, scale bar, off-chart aerodrome chevron,
  mobile bottom sheet with three detents.
- **The tension:** `design-plan.md` §6 also says "this is a MapLibre *style*, not a
  basemap — the same layer stack points at a vector source in production", so the
  design anticipated this. But an in-page chart works offline and renders into the
  dossier; a tiled basemap does neither, and needs `NEXT_PUBLIC_MAP_STYLE_URL`.
- **My recommendation:** MapLibre GL as the surface in the wizard (spec wins), with the
  designed layers ported as MapLibre style layers over a keyless basemap, **and** the
  existing SVG renderer retained as the server-side static map render for the DOCX
  (spec §7.6 needs a static map image anyway). You lose nothing and the dossier keeps
  a vector map. Confirm.

### 5.2 Derivation tree: React Flow + dagre vs the hand-laid SVG

- **Spec §10:** React Flow with a dagre layout, collapsible nodes, citation chip on
  every node, "copy trace" emitting the whole tree as markdown.
- **Design:** `motion.md` specifies the verdict sequence to the millisecond — edges
  drawing leaves→root on `stroke-dashoffset` with a 60 ms stagger, nodes settling 40 ms
  behind their incoming edge, the root plate at 1020 ms, figure count-up once. The
  current `DerivationTree.tsx` implements exactly that on a fixed 960×520 canvas, plus
  the mobile indented outline the design requires.
- **The tension:** React Flow gives dagre layout and real collapsing (needed once the
  trace is a variable-size tree from clingo rather than ten fixed nodes — so the spec
  is right for the long run), but the orchestrated draw has to be rebuilt as custom
  edge components, and the fixed `POS`/`EDGES` choreography is lost.
- **My recommendation:** React Flow + dagre (spec wins), custom node and edge
  components reproducing the design's node anatomy and the `edge-draw` / `node-settle`
  timings, keeping the existing mobile outline as the `<480px` treatment. Budget: this
  is most of a day of fiddly motion work. Confirm it is worth it versus keeping the
  working SVG tree and adding collapsing to it.

### 5.3 Tailwind v4 CSS-first vs `tailwind.config.ts`

- **Spec §10:** copy `design/tailwind.theme.ts` into the Tailwind config; spec §3's tree
  lists `frontend/tailwind.config.ts`.
- **Reality:** the frontend is on Tailwind v4, which is CSS-first — the theme lives in
  an `@theme inline` block in `app/globals.css`, and `design/project/tailwind.theme.ts`
  is a v3-shaped `Partial<Config>`. The design bundle's own note says tokens.css is the
  single source of truth and the theme file is the surface over it.
- **My recommendation:** stay on Tailwind v4 CSS-first. `tokens.css` is copied verbatim
  from the design either way, so the palette is not re-derived — which is the rule the
  spec is actually protecting. `tailwind.theme.ts` stays reference-only. Confirm.

### 5.4 Phase 5 DoD points at a file that does not exist

Spec §12 Phase 5: "the verdict screen matches `/design/screens/verdict.html`". There is
no `design/screens/` directory. The verdict design is `design/project/SORA Copilot.dc.html`
lines ~422–562 plus `design/project/screenshots/02-*.png`. I will treat those as the
reference. No action needed from you unless you have another file.

---

## 6. Where I think the spec is wrong or underspecified

1. **`igrc.csv` is missing the speed dimension.** Spec §6.2 defines rows as "max
   characteristic dimension bands (1 m / 3 m / 8 m / 20 m / 40 m)". In SORA 2.5 the
   iGRC columns are **dimension *and* max speed pairs** — 1 m/25 m/s, 3 m/35 m/s,
   8 m/75 m/s, 20 m/120 m/s, 40 m/200 m/s — and an aircraft falls in the first column
   where *both* limits hold. Dropping speed changes determinations for a small, fast
   aircraft. I plan to transcribe with a speed column. Confirm.
2. **"assembly" as a density column.** Spec §6.2 lists `assembly` alongside the
   numeric density bands. In SORA 2.5 an assembly of people is not a density band; it
   forces the top row. I plan to model it as a precondition that pins the band, not as
   a column. Confirm.
3. **`altitude_band: below_500ft | above_500ft` vs the 150 m threshold.** 500 ft is
   152.4 m. The ARC decision tree keys on 500 ft AGL; the design copy says "above
   150 m AGL". For a flight planned at 151 m these disagree on ARC, and therefore on
   SAIL. I plan to use **500 ft = 152.4 m** as the rule and correct the UI label to
   "above 500 ft (152 m)". This is a copy change to approved design text, so I need your
   sign-off.
4. **Containment is specified two ways.** Spec §6.2 wants `containment.csv` →
   a computed containment requirement; the design and the existing build deliberately
   return "assessment required" and compute nothing, on the grounds that containment
   depends on the adjacent area. I will follow the spec and compute it from the
   transcribed table — but it stays UNVERIFIED until you supply the containment
   section, and until then the UI says "assessment required" with the UNVERIFIED banner
   rather than showing a number I cannot source.
5. **The client-side TypeScript engine is live in the UI right now.** The public
   checker and the verdict screen compute SAIL in TypeScript today. Until Phase 3/7
   cut them over, the app would show a SAIL that clingo did not produce — which is the
   one thing the product must never do. Options: (a) leave them working and label them
   "preliminary estimate, client-side" until cutover, (b) disable the checker until
   Phase 7 and gate the fixture verdict pages behind an explicit demo flag. **I
   recommend (b)** — it is a compliance product and a labelled estimate is still a
   number a user can screenshot. Your call.
6. **`llm_calls` cap enforcement needs a counter the free tier can serve.** Spec §7.4
   wants a hard monthly cap enforced *before* the call. A `count(*)` per call is fine
   at this volume; I will do that and note it as a scaling item rather than add Redis
   (which is forbidden anyway).
7. **`rasterio` plus a bundled GHSL raster conflicts with "static export" and size.**
   See §7.5 — it needs a decision from you, not just a note.
8. **Phase 8 "blocked at the correct plan limit" has no limits defined.** The design's
   `TIERS` in `src/data/marketing.ts` has five tiers but no quotas. I will need the
   per-tier dossier/operation/LLM-call limits from you at Phase 8.

---

## 7. Blockers — what I need from you before Phase 1 can finish

### 7.1 Supabase project and keys *(blocks the Phase 1 DoD)*
I cannot create a Supabase project. Please create one in an **EU region**, enable
`postgis` + `pgcrypto`, and give me `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
`SUPABASE_JWT_SECRET`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
Without them I can build and test everything else, and migration 001 will be written
and reviewable, but "I can sign up and land on an empty dashboard" cannot be
demonstrated. If you would rather not paste keys here, I will finish Phase 1 with the
auth path written and unit-tested against a mocked JWT, and you verify sign-up locally.

### 7.2 `docker build` cannot run in this session
The Docker CLI is present but **the daemon is not running** in this cloud container, so
I cannot execute the Phase 1 `docker build` check myself. I will write the Dockerfile,
verify every dependency resolves (already confirmed: clingo 5.8.2, z3 5.3.0, clorm
1.6.3, supabase 2.32.0 all have manylinux/py3 wheels), and lint it — then you run
`docker build backend/` locally and paste the result. Tell me if you would rather I
find another way to prove it.

### 7.3 Anthropic model id
Spec §13 pins `ANTHROPIC_MODEL=claude-sonnet-4-6`. That is not a current model id —
the current generation is Claude 5 (`claude-sonnet-5-5`, `claude-opus-5-5`). The value
is already env-driven, so this is just a default. I propose defaulting to
`claude-sonnet-5-5`. Confirm, or give me the id you want.

### 7.4 The official SORA 2.5 source documents *(blocks verification, not Phase 1)*
Your hard rule 3 forbids inventing regulatory values, and I will not. To transcribe the
seven tables I need the **JARUS SORA 2.5 main body** plus **Annexes B, C and D**, and
the **Austrian national annex** for `90_national_at.lp`. Until you provide them every
table ships `verified: false`, surfaces in `Determination.warnings`, and shows the
UNVERIFIED banner in the verdict UI. Exact files in §8.

### 7.5 Population density raster
Spec §7.1 wants a downsampled GHSL / Eurostat GEOSTAT 1 km raster for AT + DE bundled
as a static asset. Three questions: (a) may I download GHSL R2023A myself (free,
CC BY 4.0, needs attribution) or will you supply the file? (b) AT + DE only, or EU-wide?
(c) it must be versioned into `geo_facts.raster_version` for reproducibility — confirm
you want the raster bundled with the backend image rather than held in Supabase Storage.

### 7.6 Answers to §5.1, §5.2, §5.3, §6.3 and §6.5
Those five change what I build, not just how. §5.1 (MapLibre), §5.2 (React Flow),
§5.3 (Tailwind), §6.3 (500 ft vs 150 m), §6.5 (what the UI shows before clingo lands).

### 7.7 Git workflow confirmation
Your handoff says commit straight to `main` and push, no PRs. My session configuration
designates a feature branch instead. I am following your instruction — `main` — and
noting it here so there is no ambiguity later.

---

## 8. Files you will need to fill in

### 8a. The rulebase (UNVERIFIED)

All under `backend/app/engine/rulebase/sora_2_5/tables/`. Each ships with a header block
naming document / version / section / page and `verified: false`, and seed values taken
from the spec §6.3 matrix and the existing TypeScript rulebase — **never from guesswork**.

| File | Needs | Source to transcribe from |
|---|---|---|
| `igrc.csv` | dimension+speed columns × density rows → iGRC | SORA 2.5 main body, iGRC table |
| `m1_m2.csv` | mitigation × robustness → GRC delta, + preconditions | SORA 2.5 Annex B |
| `arc.csv` | airspace class × altitude band × environment → initial ARC | SORA 2.5 Annex C |
| `sail.csv` | final GRC × residual ARC → SAIL | SORA 2.5 main body, SAIL matrix |
| `oso.csv` | SAIL × OSO → required robustness, + title and citation | SORA 2.5 main body, OSO matrix |
| `containment.csv` | SAIL / GRC conditions → containment level | SORA 2.5 containment section |
| `tmpr.csv` | residual ARC → TMPR | SORA 2.5 Annex D |
| `buffers.csv` | contingency + ground-risk-buffer parameters | SORA 2.5 / Annex B buffer method |
| `citations.csv` | rule id → document, section, page, url | the same documents |
| `cf_costs.csv` | effort cost per counterfactual parameter | **mine, not regulatory** — needs your review, not a source |

Four more tables were added during Phase 2 and are in the same state:
`igrc_columns.csv` (the dimension/speed column bands, which the spec's matrix dropped),
`thresholds.csv`, `arc_residual.csv` and `density_environment_hint.csv`. The last is
**ours, not regulatory** — it maps a population density to a *suggested* ground
environment that the operator confirms, and it never suggests `controlled` or
`assembly`. `make rulebase` prints the live list.

One known content question: the rulebase uses **17 OSOs** (#01–09, 13, 16–20, 23, 24)
because that is SORA 2.5; the design copy says "~24 OSOs", which is SORA 2.0. The count
is derived from the table rather than written anywhere.

### 8b. The country packs (UNVERIFIED)

`backend/app/national/packs/at.json` — 14 items covering the Austro Control process, the
forms and the attachments. Every one is `"provenance": "seed"` with a `source` field
saying what to check it against. Set `provenance` to `"official"` and put the document
and clause in `source` once you have confirmed an item; the UNVERIFIED banner disappears
on its own when the last one flips, in the app and in the dossier's Appendix C alike.

Deliberately absent, and the reason three items read "UNKNOWN — ask the authority":

- the application form's exact name and version,
- the fee,
- the statutory lead time,
- the minimum sum insured.

A test fails if an unverified item ever quotes a figure, and a second test fails if the
dossier's appendix renders one. `backend/app/national/packs/de.json` is a stub with the
LBA named and nothing else; `eu.json` covers "no member state chosen".

The engine's national overrides are separate and still empty on purpose:
`backend/app/engine/rulebase/sora_2_5/90_national_at.lp` and `90_national_de.lp` assert
only that the country uses the EU baseline, and say so in the trace. Nothing in a country
pack can change a determination.

---

## 9. Phase roadmap and what I will not do

Phases exactly as spec §12: **1** skeleton · **2** engine v1 in clingo, no web ·
**3** data + API · **4** geo + intake wizard · **5** verdict + counterfactuals ·
**6** dossier + conversational intake · **7** marketing + free checker + Austria pack ·
**8** billing + deploy.

At each boundary I stop, run that phase's DoD checklist, show you the output including
passing tests, and wait. I will not run into the next phase, and I will not mark
something done that is stubbed — a module that is not built raises `NotImplementedError`
rather than returning a plausible value.

Standing constraints I am holding to: free tier only (no Redis, no Celery, no always-on
worker, no paid service beyond the Anthropic key); the LLM never computes a
determination, enforced by `tests/test_boundary.py` from the first backend commit; every
determination carries a full trace, citations and a pinned rulebase version; no invented
regulatory values; engine changes ship with passing golden tests.

---

## 9a. Decisions taken under standing authority (16 Oct 2026)

Asked to complete the product and given latitude to decide, these are the calls made and
why. Each is reversible; none invents a regulatory value.

| Decision | Instead of | Why |
|---|---|---|
| **No Dockerfile.** `python main.py`, `pip install .` | Multi-stage image | Asked for directly. It also removes the only reason the backend needed native libraries. |
| **fpdf2 for PDF** | WeasyPrint + HTML/print CSS | WeasyPrint needs cairo, pango and a system font. Those existed *because* of the Dockerfile; keeping them would have put the complexity back in the host's lap. fpdf2 is pure Python and sits behind the same `Writer`, so the cross-format guarantee is unchanged. |
| **Bundle DejaVu Sans** (1.4 MB) | Rely on `fonts-dejavu-core` | Without a usable face the dossier renders blank boxes and the map chart is illegible — and neither fails loudly. A font in the repo is the only version that behaves the same on a laptop, on Render and in CI. |
| **Declare `package-data`** | Editable installs only | The rulebase, the packs, the migrations and the fonts are not Python. `pip install .` was already shipping a backend that imported cleanly and then could not render a determination. |
| **A seeded worked example** | A static demo page or screenshots | An empty dashboard explains nothing, and a fixture would show the product working without demonstrating it. §ARCHITECTURE has the reasoning. |
| **A browser smoke suite** | Trusting the unit tests | The derivation tree had never rendered and every test passed. Geometry assertions are the only thing that catches that class of fault. |

---

## 10. Phase state

Every phase is implemented. The checks below are what was actually run, not a plan.

| Phase | State | Definition of Done, as checked |
|---|---|---|
| **1** Skeleton | done | Both sides run with one command and no configuration. `/healthz` answers. Static export builds. Migration 001 executed against a real Postgres 16 (PostGIS and the Supabase schemas shimmed) — 12 tables, RLS enabled *and* forced, the sign-up trigger, the generated kinetic-energy column, the empty-trace refusal, the idempotency index, the buckets. |
| **2** Engine v1 | done | The whole chain in clingo: iGRC → M1/M2 → GRC → ARC → residual ARC → SAIL → OSOs → containment → TMPR. `because/3` on every conclusion, with an integrity constraint that makes an unjustified conclusion *unsatisfiable* — proved by injecting one and watching the solver refuse. 13 golden cases. `--models=2` on every run, so a non-deterministic rulebase fails rather than picking. CSV→LP generation refuses a malformed table. |
| **3** Data + API | done | 68 OpenAPI paths, a generated TypeScript client, org scoping resolved from the verified JWT and never from a request body. `MemoryRepo` and `SupabaseRepo` behind one Protocol, so every API test describes behaviour both must provide. |
| **4** Geo + wizard | done | Volume derivation in an equal-area projection centred on the operation, refusing a self-intersecting outline; every derived figure carries the rule and the inputs that produced it. Seven-step wizard with fact confirmation. |
| **5** Verdict + counterfactuals | done | React Flow + dagre derivation tree with the design's draw-and-settle motion. Counterfactual search runs the **real engine** on each candidate — single changes first, then bounded pairs (0.6 s) — so a suggestion that would not actually lower SAIL cannot be offered. |
| **6** Dossier + intake | done | DOCX with the full justification appendix; a test asserts every risk value in the document equals the stored determination. Evidence upload with type and size validation. The intake model proposes facts and nothing else: its tool schema has no field a conclusion could go in. |
| **7** Marketing + checker + Austria | done | The public checker answers from the same engine, rate-limited per IP without Redis. The Austria pack ships as structured, per-item-verifiable data rendered both in the app (`/app/authority/`) and into the dossier as Appendix C. Germany is a stub; the EU pack covers "no member state chosen". |
| **8** Billing + deploy, seats | done | Stripe Checkout and a webhook that verifies the signature before reading a field and claims the event id before running a handler. Plan gating on fleet, operations, determinations, dossiers, evidence, the advisor and the prose panel, each refusing with a 402 carrying the feature, the limit, the usage and the plan that lifts it. Migration 002 executed against real Postgres. `backend/scripts/smoke.sh` walks the whole product against a deployed host. Members and invitations too, so the Team plan's five seats are a thing that exists rather than a line on a pricing page: an invitation stores an address and is claimed from a verified sign-in, with no emailed link and so no sixth third-party service. |

### What a reviewer should be suspicious of, and where to look

- **"The LLM never decides anything."** `tests/test_boundary.py` walks the AST of real
  source files and checks reachability *transitively*. An earlier version recorded only
  package names and so passed with a real two-hop path to the database in place; it was
  rewritten and then verified by inserting that violation and watching it fail. The same
  file now covers Stripe.
- **"Every determination carries a trace."** Not a convention — an integrity constraint
  in `00_core.lp`, plus a check constraint in migration 001 that refuses a row with an
  empty trace.
- **"No invented regulatory values."** 14 of 14 rulebase tables and 14 of 14 Austria pack
  items are marked unverified, in the data *and* in the UI *and* in the dossier. A test
  fails if an unverified pack item ever quotes a fee, a duration or a sum insured.
- **Plan gating cannot leak existence.** Ownership is checked before the plan gate on
  every operation-scoped endpoint, so another organisation's operation answers 404 and
  not 402. There is a test for each one.
