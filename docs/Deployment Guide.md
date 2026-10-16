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

1. Create a project in an **EU region** (Frankfurt or Dublin — the settings screen lets
   an operator choose, so pick the one you will offer first).
2. SQL Editor → run the migrations **in order**:
   - `backend/app/db/migrations/001_init.sql` — enables `postgis` and `pgcrypto`,
     creates every table with RLS enabled and forced, and seeds rulebase `2.5.0-rc1`.
   - `backend/app/db/migrations/002_billing.sql` — subscriptions, dossier credits and
     the webhook's idempotency log.
   - `backend/app/db/migrations/003_invites.sql` — organisation invitations, so a Team
     plan's seats can be used.
   - `004_rulebase_rc2.sql` — adds rulebase `2.5.0-rc2` and makes it the current one.
     It inserts a row rather than editing `2.5.0-rc1`, because determinations pin the
     version they were computed against, and a stored record has to keep describing
     itself correctly.
3. Authentication → Providers → Email: enable email, and enable magic links.
4. Authentication → URL Configuration → Redirect URLs: add
   `http://localhost:3000/app/` and `https://<your-pages-domain>/app/`. Magic links
   fail silently without this.
5. Project Settings → API: copy the project URL, the anon key and the service-role key.
   JWT Settings: copy the JWT secret.
6. Storage: the migration creates `evidence`, `dossiers` and `public-assets`. The first
   two are private and reached only through backend-minted signed URLs.

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
6. Check that the UNVERIFIED banner is visible wherever a risk value appears. If it is
   not, something is claiming verification it does not have.

`scripts/smoke.sh` runs steps 1–5 against a deployed host from the command line:

```bash
BASE=https://<render-host> SUPABASE_JWT_SECRET=... backend/scripts/smoke.sh
```

## Local development

```bash
cd backend  && python main.py   # http://localhost:8000 · docs at /docs
cd frontend && npm run dev      # http://localhost:3000
```

`make dev` does the same thing and creates the virtualenv first. `python main.py --help`
lists the flags.

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
