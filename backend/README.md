# SORA Copilot — backend

FastAPI, Pydantic v2 and a clingo rules engine. **A determination is computed by the
solver and by nothing else**; everything in this service exists either to get facts into
the engine or to carry what comes out of it to a document, a database or a browser.

The system-level narrative — why ASP, why no SMT, where the neurosymbolic boundary runs
— is in the [root README](../README.md). This document is the developer's view: how to
run it, how it is laid out, and what every package is responsible for.

---

## Run it

**Python 3.12 or newer.** Check with `python3 -V` before anything else: on an older
interpreter `pip install` refuses with *"requires a different Python"* and installs
**nothing**, so the next error you see is a missing dependency that looks unrelated.

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python main.py          # http://localhost:8000 · OpenAPI docs at /docs
```

On a system whose `python3` is older, the quickest route that changes nothing else:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
.venv/bin/python main.py
```

Or `make dev`, which creates the venv, installs and runs.

**There is no Dockerfile and nothing to build.** Every dependency is a Python wheel, and
the PDF renderer and the dossier map chart carry their own typeface in
`app/assets/fonts/`, so a checkout plus `pip install` is a working backend on any machine
with Python 3.12 — which is also why this deploys on any host that can run Python.

It runs with **no environment configuration at all**: auth, persistence, the intake model
and payments each report themselves as unconfigured rather than crashing, and the startup
banner says which. See [`../.env.example`](../.env.example) and
[`../docs/ENV Example.md`](../docs/ENV%20Example.md).

```bash
.venv/bin/python main.py --help       # flags
.venv/bin/python main.py --port 9000
.venv/bin/python main.py --prod       # no reload, all interfaces, $WEB_CONCURRENCY workers
```

### Commands

```bash
make install      # venv + editable install with dev extras
make dev          # run with reload on $PORT (default 8000)
make serve        # run the way a host runs it: no reload, all interfaces
make test         # pytest
make lint         # ruff + mypy --strict
make fmt          # ruff --fix and format
make rulebase     # regenerate the .lp fact files from the transcribed CSV tables
make openapi      # write openapi.json — the input to the typed frontend client
make migrate      # apply the SQL migrations (needs $DATABASE_URL)
make migrate-status   # say what would run; change nothing
make bundle       # regenerate migrations/bundle.sql for the Supabase SQL editor
make smoke        # walk the whole product against a running API ($BASE)
make clean        # drop the venv and the caches
```

`python scripts/build_rulebase.py --strict` is the CI form of `make rulebase`: it fails
if any table is still unverified, so a seed value can never silently ship.

### The engine without the web stack

The engine is the product's credibility, so it has to be runnable and reviewable on its
own — no server, no database, no network:

```bash
.venv/bin/python -m app.engine.cli --example > mission.json
.venv/bin/python -m app.engine.cli mission.json                    # chain, trace, warnings
.venv/bin/python -m app.engine.cli mission.json --json             # machine-readable
.venv/bin/python -m app.engine.cli mission.json --counterfactuals  # minimal-change search
```

---

## Layout

```
main.py          the entry point: `python main.py`
app/
  main.py        FastAPI app, CORS, RFC 7807 handlers, startup banner, /healthz
  config.py      pydantic-settings; production refuses to start under-configured
  deps.py        JWT verification and org scoping — the real authorisation gate
  problem.py     RFC 7807 problem+json with a machine-readable `code`
  domain/        Pydantic models — the vocabulary shared with the engine and frontend
  engine/        PURE. No network, no LLM, no database. Enforced by tests/test_boundary.py
    rulebase/    transcribed CSV tables + the clingo rules that reason over them
  services/      orchestration, geometry, documents, billing, and llm.py
  api/v1/        routers; transport only
  national/      country packs: the administrative half of an application
  db/            Supabase client (service role) and numbered SQL migrations
  assets/fonts/  DejaVu Sans, bundled so documents render the same everywhere
scripts/         rulebase build, OpenAPI export, migrations, smoke
tests/           golden missions, boundary, determinism, trace, API flow
```

### `app/domain/` — the shared vocabulary

Pydantic models used by the engine, the API schemas and (via the generated TypeScript
types) the frontend. `common.py` holds the enums the regulation uses and the altitude
band threshold; `mission.py` the operator's inputs; `determination.py` the computed
chain; `oso.py` the objectives and robustness levels; `trace.py` the derivation graph;
`fields.py` the field labels and the allowlist of fields a model proposal may touch.

Nothing in `domain/` reaches a database or a solver. It is the contract between layers,
which is why the engine may import it and nothing else from the application.

### `app/engine/` — the pure core

| Module | Responsibility |
| --- | --- |
| `runner.py` | Facts in, `Determination` out. Loads the rulebase, grounds the mission, solves with `--models=1`, hands the single answer set to the trace formatter |
| `facts.py` | `Mission` → ground atoms |
| `trace.py` | `because/3` justification atoms → the derivation tree; refuses a rule with no citation |
| `scale.py` | Dimension and speed banding |
| `counterfactual.py` | Bounded combination search: size 1, then size 2, each candidate re-run through clingo |
| `cli.py` | The standalone command above |
| `rulebase/loader.py` | Reads the CSV tables with their provenance headers and verified flags |
| `rulebase/generate.py` | CSV → clingo fact files; refuses to emit anything on a malformed table |

Three failure modes are deliberately loud rather than forgiving:

- **No model.** Unsatisfiable means an integrity constraint fired — an invalid mitigation
  claim, a conclusion without a justification, a mission the ARC tree does not cover. The
  runner re-solves against a diagnostic program to say *which*, because "unsatisfiable"
  is not something an operator can act on.
- **More than one model.** That is a rulebase bug, not runtime ambiguity. Asserted on.
- **A rule with no citation.** Refused by the trace formatter.

### `app/services/` — everything stateful

`determination.py` is the gate: it reads only facts whose status is **confirmed**, so
there is no code path from a model proposal to a determination. `geo.py` derives the
contingency volume, ground risk buffer and adjacent area, reprojecting to a local
equal-area CRS for all area and buffer arithmetic, and classifies density into the band
the iGRC table defines — reading the ceilings from that table so the two cannot disagree.
`llm.py` is the only module permitted to import `anthropic`. `docwriter.py` renders one
content path to both DOCX and PDF, so the two cannot drift. `demo.py` builds the worked
example through the real engine rather than from a fixture.

### `app/api/v1/` — transport only

Routers are mounted twice by `app/main.py`, at the root and under `/api/v1/`, so
`/healthz` is reachable where an uptime monitor looks for it. `schemas.py` holds every
request and response model, and is therefore the OpenAPI surface the frontend client is
generated from. Errors are RFC 7807 `application/problem+json` with a machine-readable
`code`, so a client branches on the code and never on prose.

`/healthz` is shallow and stays green while the database is paused — by design, so an
uptime ping cannot mask a problem; `/healthz/deep` is the one that reports the database.

---

## The boundary

`app/engine/**` may import only the standard library, `clingo`, `clorm`, `z3`, `pydantic`
and `app.domain`. `app/services/llm.py` is the only module permitted to import
`anthropic`, and it has no import path — **transitively**, not merely directly — to the
engine, the database or the determination service, which is why it reads field metadata
from `app.domain.fields`.

`tests/test_boundary.py` walks the AST of every file and fails the build if that ever
changes. It also asserts that `llm.py` never writes to the `determinations` table. The
narrative is in [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

---

## The rulebase

`app/engine/rulebase/sora_2_5/` is the encoded regulation. Logic programs are numbered in
the order the chain runs:

```
00_core.lp          declarations and the defeasible-override pattern
10_igrc.lp          intrinsic ground risk class
20_mitigations.lp   M1(A)/M1(B)/M1(C)/M2 → final GRC
30_arc.lp           initial and residual air risk class
40_sail.lp          GRC × residual ARC → SAIL
50_oso.lp           objective expansion with robustness levels
60_containment.lp   containment tiers and adjacent-area requirements
70_sts_pdra.lp      the STS/PDRA override contract — fires for nothing until one is transcribed
90_national_at.lp   Austria · 90_national_de.lp Germany (baseline only)
```

**Every regulatory value is transcribed, never invented.** Each CSV in `tables/` carries
a header block naming the document, version, section and page it came from plus a
`verified: true|false` flag; `citations.csv` maps each rule id to its source. A table with
`verified: false` adds a warning to every determination that reads it and raises an
UNVERIFIED banner in the UI.

The generated `.lp` fact files are **not** hand-edited. The loop is: edit the CSV, run
`make rulebase`, re-run the golden tests.

Rulebase `2.5.1` carries fourteen tables, all verified. Eleven are transcribed from the
EASA Easy Access Rules carrying the SORA 2.5 package; three — `citations.csv`,
`density_environment_hint.csv` and `cf_costs.csv` — are **the project's own, not the
regulation's**, say so in their provenance header, and can order a list or prefill a form
but never change a determination. `CHANGELOG.md` in the version directory records what moved
between rulebase versions and why; [`../docs/RULEBASE.md`](../docs/RULEBASE.md) covers
how verification works and which corrections changed a verdict.

The **country packs** in `app/national/packs/` are the exception, and say so in their own
`summary`. `at.json` is this project's reading of the Austrian process, not a
transcription of anything Austro Control published; every item is marked UNVERIFIED in
the app and in the dossier. Nothing in a pack can change an iGRC, a GRC, an ARC, a SAIL,
an OSO or a containment level.

---

## Tests

```bash
make test                       # everything
.venv/bin/pytest tests/test_engine_golden.py -q
```

| Test | What it protects |
| --- | --- |
| `test_boundary.py` | The neurosymbolic boundary, by AST inspection |
| `test_engine_golden.py` | 17 worked missions in `tests/golden/`, including cases that must be *refused* (a mitigation claimed at a robustness the methodology does not permit, M2 claimed with no parachute fitted) |
| `test_engine_determinism.py` | One answer set, always |
| `test_engine_trace.py` | Every conclusion carries its justification |
| `test_engine_counterfactual.py` | Minimality and ranking of suggestions |
| `test_rulebase_tables.py` | Provenance headers, verified flags, malformed rows |
| `test_api_flow.py` | Intake → confirmation → determination → dossier, end to end |
| `test_packaging.py` | The non-Python files (`.lp`, CSV, JSON, SQL, fonts) actually ship in the wheel |

A change to the engine does not land with a failing golden case.

---

## Database

The running backend talks to Supabase over **PostgREST** and never opens a Postgres
socket, so `DATABASE_URL` is a migration-time variable only and does not belong in the
deployed environment.

`app/db/migrations/` is numbered SQL applied in order. `001_init.sql` needs `postgis` and
`pgcrypto` and creates every table with row-level security on, the sign-up trigger, the
three storage buckets and the first rulebase version. Apply them with `make migrate`
(keeps a ledger in `public.schema_migrations`, so re-running is safe) or paste
`migrations/bundle.sql` into the Supabase SQL editor — the two agree. Details in
[`app/db/migrations/README.md`](app/db/migrations/README.md) and
[`../docs/Supabase Setup.md`](../docs/Supabase%20Setup.md).

Row-level security is the authorisation boundary. The backend derives organisation
identity exclusively from the verified JWT in `deps.py`, never from a request body.

---

## Contract with the frontend

```bash
make openapi                 # backend/openapi.json
cd ../frontend && npm run gen:api   # → src/lib/api-types.ts
```

The TypeScript client is generated from the OpenAPI schema, so a backend field change
stops the frontend type-checking rather than failing at runtime. Regenerate both whenever
`app/api/v1/schemas.py` changes.
