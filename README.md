# SORA Copilot

**From mission to dossier in minutes.**

A European aviation-compliance web app for professional drone operators. Under EU
2019/947 a specific-category flight — beyond visual line of sight, over people, near an
aerodrome — needs a **SORA**: a formal risk assessment submitted to the national
aviation authority. A consultant charges €1,000–5,000 and takes weeks.

The operator describes the mission. A symbolic rules engine computes the official risk
chain. The app emits an authority-ready dossier in which every conclusion cites the rule
that produced it.

```
drone size + speed + what's underneath → iGRC (1–10)
  + mitigations M1(A)/M1(B)/M1(C)/M2   → GRC   (final ground risk class)
airspace + altitude + aerodrome        → ARC   (a / b / c / d)
  + strategic mitigation               → residual ARC
GRC × residual ARC                     → SAIL  (I–VI)
SAIL                                   → the OSO set at Low/Medium/High robustness,
                                         then containment
```

**Every line cites its rule.**

> SORA Copilot prepares and verifies your risk assessment. Your national aviation
> authority grants the authorisation.

## The invariant

**The language model never computes a determination.** Risk values come from the clingo
rules engine and from nowhere else; the model turns conversation into candidate facts the
operator confirms, and turns engine output into prose. That boundary is enforced by
import isolation, by an AST test that fails the build if it is ever crossed, and by a
data-flow gate in which an unconfirmed fact has no path to the engine. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run it

Two commands, one per side.

```bash
# backend — http://localhost:8000 · API docs at /docs
cd backend && make dev

# frontend — http://localhost:3000
cd frontend && npm install && npm run dev
```

Both run with **no configuration at all**. Authentication and persistence report
themselves as unconfigured rather than crashing, so you can see the whole thing before
creating a Supabase project.

To sign in and persist anything, copy `.env.example` to `backend/.env` and
`frontend/.env.local`, fill in the Supabase keys, and apply the migrations in
`backend/app/db/migrations/` in order. Which dashboard each credential comes from is in
[Third Party Setup Guide](docs/Third%20Party%20Setup%20Guide.md); how the pieces are
deployed is in [docs/DEPLOY.md](docs/DEPLOY.md).

### Checks

```bash
cd backend  && make test      # pytest
cd backend  && make lint      # ruff + mypy --strict
cd backend  && make rulebase  # which regulatory tables are still unverified
cd frontend && npm run build  # static export to out/; also type-checks

# the whole product, against a running backend
BASE=http://127.0.0.1:8000 SUPABASE_JWT_SECRET=... backend/scripts/smoke.sh
```

## ⚠ No regulatory table is verified yet

Every value in the rulebase is a **seed**, not a transcription from the official
document. Determinations carry an `UNVERIFIED` warning, and the verdict screen shows a
banner. This is deliberate: a plausible guess in a compliance product is worse than a
visible gap.

`make rulebase` lists exactly which files need filling in. Verifying them needs the JARUS
SORA 2.5 main body, Annexes B, C and D, and the Austrian national annex. See
[docs/RULEBASE.md](docs/RULEBASE.md) and [PLAN.md](PLAN.md) §8.

The same applies to the **country packs**. `backend/app/national/packs/at.json` is this
project's reading of the Austrian process, not a transcription of anything Austro Control
published. Every item is marked UNVERIFIED in the app and in the dossier's Appendix C,
and none of them quotes a fee, a lead time or a sum insured — a plausible number in a
compliance product is worse than an honest gap.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Rules engine | clingo (Answer Set Programming) |
| Counterfactuals | bounded enumeration over the real engine |
| Geospatial | shapely, pyproj, PostGIS |
| Documents | python-docx, WeasyPrint |
| Language model | Anthropic, for intake and prose only |
| Database | Supabase Postgres (EU) + PostGIS + RLS |
| Auth | Supabase Auth — email and magic link |
| Frontend | Next.js 15 App Router, static export, TypeScript, Tailwind v4, Framer Motion |
| Payments | Stripe Checkout + a signature-verified, idempotent webhook |
| Hosting | Render (backend) · Cloudflare Pages (frontend) · Supabase (database) |

Free tiers throughout.

## Layout

```
backend/    FastAPI, the clingo rulebase, services, API
frontend/   Next.js static export
design/     the approved design system and screens — READ ONLY
docs/       ARCHITECTURE · RULEBASE · DEPLOY · Third Party Setup Guide · the build spec
PLAN.md     the plan, the open decisions, and what is still blocked
```

## Where the build is

All eight phases of the build spec are implemented. What remains is not code: no
regulatory table has been verified against its published source, and no national annex
has been transcribed. [PLAN.md](PLAN.md) has the phase-by-phase state, the decisions
taken, the conflicts between the build spec and the design, and exactly which files need
filling in.
