# Deployment Guide

Two things get deployed: a **Python backend** on Render, and a **folder of static files**
for the frontend, which you upload to Cloudflare Pages (or Hostinger, or any web host —
it is just files).

Everything runs on free tiers. No Redis, no Celery, no always-on worker, no paid service
beyond the Anthropic API key, which is itself optional.

| Piece | Where | What it actually is |
|---|---|---|
| Database | Supabase, EU region, free | Postgres. Pauses after ~7 days with no traffic |
| Backend | Render — **Python** web service, Frankfurt, free | Sleeps after ~15 min idle |
| Frontend | Cloudflare Pages / Hostinger | A folder of HTML, CSS, JS and images |

EU regions throughout: data residency is a stated selling point, not an afterthought.

**Order matters.** Supabase first (the backend needs its keys), then the backend (the
frontend needs its URL), then the frontend.

**Before you start**, get the credentials. Which dashboard, which button, which line of
`.env` is in [Third Party Setup Guide](./Third%20Party%20Setup%20Guide.md); what each
variable does is in [ENV Example](./ENV%20Example.md). This page assumes you have them.

---

# PART ONE — the backend on Render

Jump to [Part Two](#part-two--the-frontend-folder) for the frontend.

## 1. Supabase

Creating a Supabase project gives you an **empty** database. It is not pre-populated:
every table this product reads and writes is created by the SQL in
`backend/app/db/migrations/`, and something has to run it — either one paste in the SQL
editor or one command, below. Neither needs the other.

1. Create a project in an **EU region** (Frankfurt or Dublin — the settings screen lets
   an operator choose, so pick the one you will offer first). Save the database password
   it shows you; it is shown once.

2. **Create the schema.** Two routes; both run the same SQL and end in the same place.

   **From the dashboard only, no terminal** — SQL Editor → New query → paste the whole
   of `backend/app/db/migrations/bundle.sql` → Run. That file is the five migrations
   concatenated in order inside one transaction, so it lands completely or not at all.
   [Supabase Setup](./Supabase%20Setup.md) is the step-by-step, including what to
   check afterwards.

   **Or from a terminal.** Press **Connect** at the top of the dashboard, choose
   **Session pooler**, and copy the URI. It looks like:

   ```
   postgresql://postgres.abcdefghijkl:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
   ```

   Replace `[YOUR-PASSWORD]` with the database password and put the whole thing in
   `backend/.env` as `DATABASE_URL=…`. Then:

   ```bash
   cd backend
   make migrate-status     # says what will run, changes nothing
   make migrate            # creates the schema
   ```

   Expect five migrations and then `5 migration(s) applied.`

   - **Use port 5432** — the session pooler or the direct connection. The transaction
     pooler on **6543** cannot run schema changes and will fail partway.
   - `DATABASE_URL` is **not** `SUPABASE_URL`. The running backend never opens a
     Postgres socket; it talks to Supabase over PostgREST. So this variable belongs in
     your local `.env` only, and **not** in Render's environment.
   - Re-running `make migrate` is safe. It keeps a ledger in `public.schema_migrations`
     and applies only what is missing, one transaction per file.
   - If you already pasted the SQL into the SQL editor by hand, run
     `backend/.venv/bin/python scripts/migrate.py --baseline` once. It records the
     files as applied without re-running them, so the ledger starts telling the truth.

   What the five create: `001_init.sql` enables `postgis` and `pgcrypto` and creates
   every table with RLS on, the sign-up trigger, the three storage
   buckets and rulebase `2.5.0-rc1`. `002_billing.sql` adds subscriptions, dossier
   credits and the webhook's idempotency log. `003_invites.sql` adds organisation
   invitations, so a Team plan's seats can be used. `004` and `005` add rulebase
   `2.5.0-rc2` and `2.5.1` and make the latter current. Each inserts a row rather than
   editing the previous one, because determinations pin the version they were computed
   against and a stored record has to keep describing itself correctly.

   The two routes agree: pasting `bundle.sql` writes the same ledger rows, so a later
   `make migrate` reports "nothing to do" rather than running everything again.

3. Authentication → Providers → Email: enable email, and enable magic links.
4. Authentication → URL Configuration → Redirect URLs: add
   `http://localhost:3000/app/` and `https://<your-pages-domain>/app/`. Magic links
   fail silently without this.
5. Project Settings → API: copy the project URL, the anon key and the service-role key.
   JWT Settings: copy the JWT secret.
6. Storage: the migration creates `evidence`, `dossiers` and `public-assets`. The first
   two are private and reached only through backend-minted signed URLs.

**Check it worked.** In the SQL editor:

```sql
select filename from public.schema_migrations order by filename;
select version, is_current, verified from public.rulebase_versions order by version;
```

Five filenames, and `2.5.1` as the only `is_current` row, with `verified` true.

**A paused project** (about 7 days of no traffic on the free tier) is restored from the
Supabase dashboard — open the project and choose Restore. It takes a few minutes and
loses no data. `/healthz` stays green while it is paused, by design;
`/healthz/deep` is the one that reports the database as unreachable.

## 2. Backend on Render

There is **no Dockerfile**. Every dependency is a Python wheel and the renderers carry
their own typeface, so a checkout plus `pip install` is a working backend — which is
also why this deploys on any host that can run Python, not only on Render.

1. New → Web Service → connect the repository.
2. Root directory `backend`, runtime **Python 3**, region **Frankfurt**, instance **Free**.
3. Build command: `pip install .`
4. Start command: `python main.py --prod`
5. Health check path `/healthz`.
6. Environment: every backend key from `.env.example`. Set `ENV=production` — the app
   refuses to start without the Supabase keys, which is the behaviour you want in
   production. Set `CORS_ORIGINS` to the Pages origin. Map `GIT_SHA` to Render's
   `RENDER_GIT_COMMIT` so `/healthz` can be traced back to a build.

`main.py` reads `$PORT`, and `--prod` binds every interface, turns off reload and
honours `$WEB_CONCURRENCY` for workers. It prints which services are configured on
startup, so the first line of the deploy log tells you whether the database, the intake
model and payments are live.

**Nothing to apt-get.** PDFs render through fpdf2 and the volume chart through Pillow,
both pure Python, and `app/assets/fonts/` ships DejaVu Sans so neither depends on the
host having a usable typeface. If that font were missing, a dossier would render as
blank boxes rather than failing loudly — which is why it is in the repository and why
`pyproject.toml` declares it as package data.

### The cold start is a product problem, not just an ops one

A free instance sleeps after ~15 minutes and takes tens of seconds to wake. Two
mitigations, both already in place:

- `frontend/src/lib/api.ts` treats 502/503/504 and network failures as *warming*, not
  errors: it retries with backoff totalling ~31 s and reports progress through
  `onWarming`, so a screen can say the service is waking instead of showing a red box.
- `/healthz` has no dependencies and is pinged by an external free uptime monitor
  (UptimeRobot or similar, 5-minute interval) to keep the instance awake during the day.

## 3. Stripe

Optional: the product runs without it, on the free plan, and says so in the plan panel.
With no `STRIPE_SECRET_KEY` nothing can be bought; with no `STRIPE_WEBHOOK_SECRET` the
webhook endpoint refuses every request rather than trusting an unverified payload.

1. Create the products and prices (Test mode first): **Pro** and **Team** as recurring
   monthly prices, **Per dossier** as a one-off price. Copy the three *price* ids
   (`price_…`, not `prod_…`) into `STRIPE_PRICE_PRO`, `STRIPE_PRICE_TEAM` and
   `STRIPE_PRICE_DOSSIER`.
2. Developers → Webhooks → add an endpoint at `https://<render-host>/api/v1/billing/webhook`
   for these events, and no others:
   `checkout.session.completed`, `customer.subscription.created`,
   `customer.subscription.updated`, `customer.subscription.deleted`,
   `invoice.payment_failed`. Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.
3. Settings → Billing → Customer portal: enable it, and allow cancellation and payment
   method updates. `POST /api/v1/billing/portal` sends customers there rather than
   rebuilding any of it.
4. Set `STRIPE_RETURN_URL` to the **frontend** origin plus the settings path, e.g.
   `https://<your-pages-domain>/app/settings/`. The checkout endpoint only ever takes a
   *path* from the caller and resolves it against this origin, so a request cannot
   redirect a payment confirmation off-site.

A plan is derived from the configured price id and from nothing else — never from a
product's name or from event metadata — so renaming a product in the dashboard cannot
change what a customer is entitled to. Every event id is recorded before its handler
runs, so a redelivery is a no-op.

Verify the endpoint with the Stripe CLI before taking real money:

```bash
stripe listen --forward-to localhost:8000/api/v1/billing/webhook
stripe trigger customer.subscription.created
```

Then confirm `GET /api/v1/billing` reports the new plan, and that sending the same event
twice answers `{"outcome": "duplicate"}`.

# PART TWO — the frontend folder

The frontend is a **static export**: `output: 'export'`, `trailingSlash: true`,
`images.unoptimized`. No SSR, no server actions, no route handlers. The build produces a
folder called `out/`, and every file a visitor needs is inside it. Any host that can
serve files will serve this.

## 4a. Build the folder

Run this on your own machine, or anywhere with Node 20+:

```bash
git clone https://github.com/roy-sub/sora-copilot
cd sora-copilot/frontend

# The NEXT_PUBLIC_* values are baked into the JavaScript at build time, so they have to
# be set BEFORE you build. Changing one later means building again — a restart does
# nothing, because there is no server to restart.
cat > .env.local <<'EOF'
NEXT_PUBLIC_SUPABASE_URL=https://<your-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your anon key>
NEXT_PUBLIC_API_URL=https://<your-render-host>
NEXT_PUBLIC_SITE_URL=https://<your-frontend-domain>
NEXT_PUBLIC_MAP_STYLE_URL=
EOF

npm install
npm run build
```

When it finishes you have **`frontend/out/`**. That is the folder to upload. Check it:

```bash
ls frontend/out/            # index.html, app/, pricing/, _next/, media/, …
du -sh frontend/out/        # a few MB
ls frontend/out/media | wc -l   # 16 — the media assets ship with the build
ls frontend/out/maplibre-gl-worker.mjs   # must exist, or the map renders nothing
```

To hand it to someone, or to upload it as a single file:

```bash
cd frontend && zip -r ../sora-copilot-frontend.zip out
```

> `npm run build` runs `npm run prebuild` first, which copies MapLibre's worker into
> `public/`. Without it the map draws an empty grid and reports no error at all, so if
> `out/maplibre-gl-worker.mjs` is missing, something skipped the prebuild step.

## 4b. Upload it — Cloudflare Pages

**Option A — connect the repository** (rebuilds automatically on every push):

1. https://pages.cloudflare.com → Create a project → Connect to Git → pick the repo.
2. Framework preset: **Next.js (Static HTML Export)**, or None.
3. Build command `npm run build`, output directory `out`, root directory `frontend`.
4. Settings → Environment variables: add every `NEXT_PUBLIC_*` from your `.env.local`.
   They are build-time, so **a change needs a redeploy**, not a restart.
5. Save and Deploy. You get `https://<project>.pages.dev`.

**Option B — upload the folder** (no Git connection, no build on their side):

1. https://pages.cloudflare.com → Create a project → **Upload assets**.
2. Drag the `frontend/out` folder in, or the zip you made above.
3. Deploy.

With Option B you rebuild and re-upload by hand whenever anything changes — including
whenever a `NEXT_PUBLIC_*` value changes.

## 4c. Upload it — Hostinger (or any other host)

1. Build the folder exactly as in 4a.
2. Hostinger hPanel → **File Manager** → open `public_html`.
3. Delete whatever is in there, then upload `sora-copilot-frontend.zip` and extract it.
4. Move the **contents of `out/`** into `public_html` so that `public_html/index.html`
   exists. A common mistake is ending up with `public_html/out/index.html`, which serves
   a directory listing or a 404.
5. If the host offers it, enable HTTPS and force it.

Two things to get right on any non-Cloudflare host:

- **Trailing slashes.** The export is built with `trailingSlash: true`, so every route is
  a real directory with an `index.html` inside it (`/pricing/index.html`). Apache and
  LiteSpeed serve this correctly out of the box. Nothing to configure.
- **The API origin.** Whatever domain the frontend ends up on must be listed in the
  backend's `CORS_ORIGINS`, or every request from the browser is blocked and the app
  looks broken while the backend looks healthy. See Part One, step 2.

## 4d. Point the backend at the frontend

Back in Render → your service → Environment:

```
CORS_ORIGINS=https://<your-frontend-domain>
STRIPE_RETURN_URL=https://<your-frontend-domain>/app/settings/
```

Then in Supabase → Authentication → URL Configuration → Redirect URLs, add
`https://<your-frontend-domain>/app/`. Magic links fail silently without it.

---

# AFTER BOTH PARTS

## 5. Media

**Nothing to do.** All sixteen assets are in `frontend/public/media/` and ship with the
build. `backend/tests/test_media_assets.py` checks each one against
`frontend/src/lib/media-manifest.ts` for pixel size, byte budget and, for the two
videos, H.264 in yuv420p — so a missing or drifted asset fails the build rather than
falling back to a placeholder nobody notices in review.

To replace one, drop a file at the manifest's path at the manifest's size and rebuild;
no code change. `?slots=1` overlays each slot's id and size budget. To rebuild them all
from the product, run `frontend/scripts/make-media.mjs` — [Media Generation
Guide](./Media%20Setup%20Guide.md) explains how each was made and carries a
finished prompt for anything you want to generate instead.

## 6. Smoke test against production

```bash
curl -s https://<render-host>/healthz | jq
curl -s https://<render-host>/healthz/deep | jq      # expect database: ok
curl -s https://<render-host>/api/v1/rulebase/current | jq '.version, .verified'
curl -s -X POST https://<render-host>/api/v1/public/category-check \
  -H 'content-type: application/json' \
  -d '{"mass_band":"4to25","ground_environment":"sparsely_populated","operation_type":"bvlos"}' | jq

# The webhook must refuse an unsigned payload. Anything but 400 is a serious problem.
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://<render-host>/api/v1/billing/webhook \
  -H 'content-type: application/json' -d '{"id":"evt_x","type":"customer.subscription.created"}'
```

Then in a browser, the build spec's definition of done:

1. Sign up and land on an empty dashboard.
2. Add an aircraft, draw a volume, answer the wizard, confirm every fact.
3. Run the determination: a SAIL with a readable derivation tree and counterfactuals.
4. Export the DOCX dossier and reopen the operation — it persisted.
5. Hit a plan limit on purpose (a fourth operation on the free plan) and check the 402
   renders as an upgrade panel with the right numbers.
6. Check that **no** UNVERIFIED banner appears on the verdict, and that
   `/api/v1/rulebase/current` reports `version: "2.5.1"` and `verified: true`. Every
   regulatory table is transcribed from the adopted EASA text, so a banner here would
   mean a table regressed to a seed — `make rulebase --strict` is the check that catches
   it before a deploy. The *country pack* warnings on `/app/authority/` are a different
   thing and should still be there: that annex has not been transcribed.

`scripts/smoke.sh` runs steps 1–5 against a deployed host from the command line:

```bash
BASE=https://<render-host> SUPABASE_JWT_SECRET=... backend/scripts/smoke.sh
```

## Local development

Needs **Python 3.12 or newer** and **Node 20+**. Check the first one before anything
else — on an older interpreter `pip install` refuses with *"requires a different
Python"* and installs **nothing**, so the error you see next is a missing dependency
that looks unrelated to the version.

```bash
python3 -V     # must be 3.12 or newer

git clone https://github.com/roy-sub/sora-copilot && cd sora-copilot

# terminal 1
cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python main.py        # http://localhost:8000 · docs at /docs

# terminal 2
cd frontend && npm install && npm run dev   # http://localhost:3000
```

No `python3.12` on the machine? This installs one for the project without touching
anything system-wide:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
cd backend && uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
.venv/bin/python main.py
```

`make dev` does the same thing and creates the virtualenv first. `python main.py --help`
lists the flags.

**Two messages that look like errors and are not.** `npm run dev` prints
`Request timed out after 3000ms … Retrying 1/3…` on a machine that cannot reach Google
Fonts: that is `next/font/google` fetching Archivo and Outfit, and after three tries it
falls back to a system face and carries on. The line that tells you the server is up is
`Ready in Ns`. And the app's own `Request failed`/warming messages in the browser mean
the backend is not running yet — the frontend treats a dead or sleeping API as *warming*
and retries rather than showing a red box.

Both run without any environment configuration. Auth and persistence report themselves
as unconfigured rather than crashing, so the skeleton is usable before a Supabase project
exists.

### Validating the migration without Supabase

`001_init.sql` can be executed against a plain Postgres 16 by shimming the
Supabase-managed pieces: create an `auth` schema with a `users` table and `uid()` /
`role()` functions, a `storage` schema with a `buckets` table, and — if PostGIS is not
installed — substitute `text` for `geography(Polygon,4326)` and drop the `using gist`
from the geography index. Everything else (constraints, generated columns, triggers,
policies, the PL/pgSQL blocks) runs unmodified, which is enough to catch real errors
before they reach the project.
