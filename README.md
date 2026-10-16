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
cd backend && python main.py

# frontend — http://localhost:3000
cd frontend && npm install && npm run dev
```

Both run with **no configuration at all**. Authentication and persistence report
themselves as unconfigured rather than crashing, so you can see the whole thing before
creating a Supabase project.

To sign in and persist anything, copy `.env.example` to `backend/.env` and
`frontend/.env.local`, fill in the Supabase keys, and apply the migrations in
`backend/app/db/migrations/` in order. Every variable is explained in [docs/ENV Example.md](docs/ENV%20Example.md); which
dashboard each credential comes from is in
[Third Party Setup Guide](docs/Third%20Party%20Setup%20Guide.md); how the pieces are
deployed is in [docs/Deployment Guide.md](docs/Deployment%20Guide.md).

### Checks

```bash
cd backend  && make test      # pytest
cd backend  && make lint      # ruff + mypy --strict
cd backend  && make rulebase  # provenance of every regulatory table
cd frontend && npm run build  # static export to out/; also type-checks

# the whole product, against a running backend
BASE=http://127.0.0.1:8000 SUPABASE_JWT_SECRET=... backend/scripts/smoke.sh
```

## Every regulatory table is verified

All fourteen tables are transcribed from the **EASA Easy Access Rules for Unmanned
Aircraft Systems**, revision of June 2026, which carries the SORA 2.5 package as AMC and
GM to Regulation (EU) 2019/947 (ED Decision 2025/018/R of 30 September 2025). Each table
cites a page, and each carries a `basis:` line saying what was checked against what.
Determinations carry no `UNVERIFIED` warning and the dossier is submittable.

`make rulebase` reports the live state; `make rulebase --strict` fails if any table ever
regresses to a seed. The rule remains that a value is transcribed or absent — a plausible
guess in a compliance product is worse than a visible gap. See
[docs/RULEBASE.md](docs/RULEBASE.md), which lists the four corrections that moved a
verdict.

The **country packs** are the exception, and say so. `backend/app/national/packs/at.json`
is this project's reading of the Austrian process, not a transcription of anything Austro
Control published. Every item is marked UNVERIFIED in the app and in the dossier's
Appendix C, and none of them quotes a fee, a lead time or a sum insured. The pack is an
operator's checklist for their authority; nothing in it can change an iGRC, a GRC, an
ARC, a SAIL, an OSO or a containment level.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Rules engine | clingo (Answer Set Programming) |
| Counterfactuals | bounded enumeration over the real engine |
| Geospatial | shapely, pyproj, PostGIS |
| Documents | one content path, rendered to DOCX (python-docx) or PDF (fpdf2) |
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
docs/       ARCHITECTURE · RULEBASE · DEPLOY · ENV Example
            Third Party Setup Guide · Media Setup Guide
PLAN.md     the plan, the open decisions, and what is still blocked
```

## Where the build is

All eight phases of the build spec are implemented and every regulatory table is
transcribed from the adopted text. What remains is not code: the Austrian national annex
has not been transcribed, and the deployment needs credentials.
[PLAN.md](PLAN.md) has the phase-by-phase state, the decisions taken and the conflicts
between the build spec and the design;
[docs/Final Manual Task.md](docs/Final%20Manual%20Task.md) records what the
transcription changed.
