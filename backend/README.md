# SORA Copilot — backend

FastAPI + a symbolic rules engine. The engine is the product's credibility: a
determination is computed by clingo and by nothing else.

## Run it

**Python 3.12 or newer.** Check with `python3 -V` before anything else: on an older
interpreter `pip install` refuses with *"requires a different Python"* and installs
**nothing**, so the next error you see is a missing dependency that looks unrelated.

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python main.py          # http://localhost:8000 · docs at /docs
```

On a system whose `python3` is older, the quickest route that changes nothing else:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
.venv/bin/python main.py
```

Or `make dev`, which does both. There is **no Dockerfile and nothing to build**: every
dependency is a Python wheel, and the PDF renderer and the map chart carry their own
typeface in `app/assets/fonts/`, so a checkout plus `pip install` is a working backend
on any machine with Python 3.12.

It runs with no environment configuration at all — auth, persistence, the intake model
and payments each report themselves as unconfigured rather than crashing, and the
startup banner says which. See `../.env.example` and `../docs/ENV Example.md`.

```bash
python main.py --help     # flags
python main.py --port 9000
python main.py --prod     # no reload, all interfaces, $WEB_CONCURRENCY workers
```

## Other commands

```bash
make test         # pytest
make lint         # ruff + mypy --strict
make fmt          # ruff --fix and format
make rulebase     # validate the transcribed tables, report what is still UNVERIFIED
make openapi      # write openapi.json, the input to the typed frontend client
make smoke        # walk the whole product against a running API ($BASE)
```

## Layout

```
main.py          the entry point: `python main.py`
app/
  main.py        FastAPI app, CORS, RFC 7807 handlers, /healthz
  config.py      pydantic-settings; production refuses to start under-configured
  deps.py        JWT verification and org scoping — the real authorisation gate
  problem.py     RFC 7807 problem+json with a machine-readable `code`
  db/            Supabase client (service role) and numbered SQL migrations
  domain/        Pydantic models — the vocabulary shared with the engine and frontend
  engine/        PURE. No network, no LLM, no database. Enforced by tests/test_boundary.py
    rulebase/    transcribed CSV tables + the clingo rules that reason over them
  national/      country packs: the administrative half of an application
  assets/fonts/  DejaVu Sans, bundled so documents render the same everywhere
  services/      orchestration, geometry, documents, and llm.py (the only anthropic importer)
                 docwriter.py renders one content path to DOCX and PDF
                 demo.py builds the worked example, through the real engine
  api/v1/        routers, added as their phase lands
tests/
  test_boundary.py   the neurosymbolic boundary, enforced by AST inspection
  golden/            worked SORA examples; engine changes may not land with one failing
```

## The boundary

`app/engine/**` may import only the standard library, `clingo`, `clorm`, `z3`,
`pydantic` and `app.domain`. `app/services/llm.py` is the only module permitted to import
`anthropic`, and it has no import path to the engine, the database or the determination
service. `tests/test_boundary.py` walks the AST of every file and fails the build if that
ever changes. Narrative in `../docs/ARCHITECTURE.md`.

## The rulebase

Every regulatory value is transcribed from an official source, never invented. Each
table in `app/engine/rulebase/sora_2_5/tables/` carries the document, section and page
it came from plus a `verified` flag. **No table is verified yet** — run `make rulebase`
to see the list, and `../docs/RULEBASE.md` for how verification works. Until then every
determination carries an UNVERIFIED warning and the verdict UI shows a banner.

## Database

Migration `app/db/migrations/001_init.sql` needs `postgis` and `pgcrypto`. Apply it
through the Supabase SQL editor or `supabase db push` — see
`app/db/migrations/README.md`.
