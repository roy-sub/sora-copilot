# SORA Copilot — frontend

Next.js 15 with the App Router, compiled to a **static export**. TypeScript, Tailwind v4,
MapLibre GL for the operational volume editor, React Flow for the derivation tree,
TanStack Query for everything that comes from the API.

There is no server-side rendering, no server action and no API route in this codebase.
All state lives behind the backend API, so the whole application is a folder of files on
a CDN edge. The system-level narrative is in the [root README](../README.md); this
document is the developer's view.

---

## Run it

**Node.js 20 or newer.**

```bash
npm install
npm run dev        # http://localhost:3000
```

It runs with **no environment configuration**: with no Supabase keys the UI states
plainly that sign-in is unavailable instead of failing opaquely, and with no map style
URL the volume editor renders its layers on a plain ground rather than a blank panel. The
backend is assumed at `http://localhost:8000` until told otherwise.

```bash
npm run build      # static export to out/ — also the type-check gate
npm start          # serve out/ locally
npm run lint       # tsc --noEmit
npm run gen:api    # regenerate src/lib/api-types.ts from ../backend/openapi.json
npm run smoke      # drive the built app in a real browser and assert geometry
```

`prebuild` and `predev` run `scripts/copy-maplibre-worker.mjs` automatically. Do not skip
it: MapLibre 6 loads its worker from a URL webpack cannot analyse, so without the copied
file the map renders **nothing** — no error, just an empty chart.

### Environment

All four are inlined at build time, so a missing value is a build-time fact, not a
runtime surprise. Copy [`../.env.example`](../.env.example) to `.env.local`.

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Auth only. The frontend never reads the database directly |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public by design, constrained by row-level security |
| `NEXT_PUBLIC_API_URL` | The backend origin (default `http://localhost:8000`) |
| `NEXT_PUBLIC_MAP_STYLE_URL` | A MapLibre style that needs no API key; optional |
| `NEXT_PUBLIC_SITE_URL` | `metadataBase`, which resolves the social-card URL at build |

---

## Layout

```
src/
  app/                       routes (App Router)
    layout.tsx               fonts, providers, theme attribute
    globals.css              Tailwind v4 entry; @theme over tokens.css
    error.tsx · not-found.tsx
    (marketing)/             page.tsx · pricing · legal · checker  — public
    (auth)/signin/           email + magic link
    app/                     the authenticated product
      layout.tsx · page.tsx  shell and dashboard
      new/                   the intake wizard
      operations/view/       the verdict surface
      dossiers/ · fleet/ · authority/ · settings/
      overlays/ · states/    design reference routes, not product surfaces
  components/
    wizard/                  Wizard · WizardStepper · IntakePanel · FactChip · MitigationCard
    verdict/                 Verdict · Chain · TraceTree · GapAnalysis · OsoDrawer
    map/                     MapVolumeEditor · MapPanels
    app/                     Shell · AuthGate · BillingPanel · MembersPanel · EmptyState
    marketing/               Chrome · Tiers · Faq
    ui/                      Button · Dialog · Field
    Brand · SailBadge · MediaSlot · Toast · PlanLimit · ComputationProgress
  lib/                       the API client, auth, query, geo, env, prefs, media registry
  data/                      static copy: marketing.ts · oso.ts
  styles/tokens.css          the token system — the single source of truth for colour
public/media/                hero, feature and empty-state assets
scripts/                     pre-build worker copy, media generation, browser smoke
```

---

## The API client

Three files, in layers, and nothing restates a backend shape by hand:

| File | Responsibility |
| --- | --- |
| `lib/api-types.ts` | **Generated.** `npm run gen:api` writes it from `backend/openapi.json`. Never edited |
| `lib/api.ts` | `fetch` with two things a bare fetch lacks (below) |
| `lib/api-client.ts` | The typed surface — one function per endpoint, types taken from the generated schema |

What `api.ts` adds:

1. **RFC 7807 problems.** Every backend error is `application/problem+json` with a
   machine-readable `code`, so callers branch on the code rather than on prose.
2. **Cold starts.** The free backend tier sleeps after ~15 minutes idle and can take half
   a minute to wake. A sleeping backend is not an error: the first call retries with
   backoff and reports `warming`, and `onWarming` lets a screen show that state instead
   of a red box.

`lib/hooks.ts` wraps the client in TanStack Query, one hook per endpoint, with array
query keys so a mutation invalidates exactly what it changed. **A determination is
invalidated by anything that touches the mission** — a determination computed from stale
inputs is the one thing this product must never show.

Uploads and downloads live in `lib/upload.ts` rather than `api.ts`, because multipart
bodies and `Blob` responses break its JSON assumptions, and because an `<a download>`
cannot carry an `Authorization` header.

When `backend/app/api/v1/schemas.py` changes: `cd ../backend && make openapi`, then
`npm run gen:api`. Drift becomes a type error rather than a runtime bug.

---

## Auth

Supabase Auth, email plus magic link, with a password form for operators who prefer one.
Static export means there is no server callback: the magic link returns to `/app/` and
`detectSessionInUrl` completes the exchange in the browser. `lib/auth.tsx` holds the
session; `components/app/AuthGate.tsx` guards the authenticated routes. The access token
is attached by `api.ts` as a bearer JWT, and the backend derives organisation identity
from it — the frontend never asserts who it is in a request body.

---

## The map editor

`components/map/MapVolumeEditor.tsx`. MapLibre GL, with the design's layer stack
preserved as style layers: flight geography in the accent, contingency volume as a dashed
accent outline, ground risk buffer in `--sail-4`, the adjacent area as a hairline ring.
The operator draws **only** the flight geography; every other volume is derived by the
backend from transcribed buffer parameters and returned as GeoJSON, so the client never
computes a regulatory geometry.

Two deliberate properties: the basemap is **optional**, so the instrument works with no
tile provider configured; and the worker file is copied at build time rather than
committed, so it can never be a stale copy of a moved dependency.

---

## The derivation tree

`components/verdict/TraceTree.tsx`. React Flow with a dagre layout, because the engine's
trace is a variable-size graph rather than the fixed canvas the design prototype used.
Edges draw from the leaves to the root over about 1200 ms and each node settles 40 ms
behind its incoming edge; under `prefers-reduced-motion` everything renders complete,
immediately.

Every node names the rule that fired and the regulatory citation it carries. The tree is
rendered from the engine's own justification atoms — nothing here reconstructs a
derivation.

---

## Styling and tokens

`src/styles/tokens.css` is the single source of truth: the Dronex brand base (black,
paper, concrete, lime), a graphite sheet ramp so a dark panel is a construction rather
than a background colour, and a six-step SAIL risk ramp that is greenless by construction
— no hue falls between 95 and 150, so a risk state can never be mistaken for the brand
accent or for "safe".

`globals.css` is the Tailwind v4 entry and exposes those tokens as the `@theme` surface.
**The ground is always black; the theme switch flips the sheets, not the page.**
`lib/prefs.tsx` holds the theme and sets `data-theme` on `<html>`.

Do not introduce a raw colour value in a component. Add the token.
[`../design/`](../design/) is the approved design system and is **read only**;
`design/project/components.md` and `motion.md` are the reference for anything new.

---

## Media

`lib/media-manifest.ts` is the single registry: one entry per slot, each carrying the
intrinsic dimensions from `design/project/media-manifest.md`. `<MediaSlot id="hero-loop" />`
reads ratio, size and description from it, so dropping a real file into `public/media/`
with the manifest filename makes it appear with zero layout shift and no code change.
`?slots=1` labels every slot in place. See
[`../docs/Media Setup Guide.md`](../docs/Media%20Setup%20Guide.md).

---

## Tests

`npm run build` is the type-check gate — the static export fails on a type error.
`npm run smoke` drives the **built** app in a real browser and asserts *pixels and
geometry*, not that components exist. It exists because of a bug it would have caught:
React Flow's structural stylesheet was never imported, so the derivation tree laid itself
out below its own container and the panel rendered blank. Every unit test passed, the
nodes were in the DOM, the API returned a 27-node trace, and nothing was wrong except
what you could see. A node is therefore counted only if its box actually intersects the
panel meant to contain it.

---

## Build and deploy

```bash
npm run build      # → out/
```

`out/` is a folder of HTML, CSS, JS and images with no runtime requirement: Cloudflare
Pages, or any static host. Set the environment variables **before** the build — they are
inlined, so changing one means rebuilding. The deployment order (Supabase, then backend,
then frontend, because each needs the previous one's URL) is in
[`../docs/Deployment Guide.md`](../docs/Deployment%20Guide.md).
