# Deployment

Where each piece goes and how it is wired. For *where to get the credentials* — which
dashboard, which button, which line of `.env` — read
[Third Party Setup Guide](./Third%20Party%20Setup%20Guide.md) instead, and for what each
variable does, [ENV Example](./ENV%20Example.md). This page assumes you already have
them.

Everything runs on free tiers. No Redis, no Celery, no always-on worker, no paid service
beyond the Anthropic API key.

| Piece | Where | Notes |
|---|---|---|
| Backend | Render — **Python** web service, Frankfurt, free | Sleeps after ~15 min idle |
| Frontend | Cloudflare Pages | `npm run build`, output `out` |
| Database | Supabase Postgres, EU region, free | Pauses after ~7 days idle |

EU regions throughout: data residency is a stated selling point, not an afterthought.

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

## 4. Frontend on Cloudflare Pages

1. New project → connect the repository.
2. Build command `npm run build`, output directory `out`, root directory `frontend`.
3. Environment: every `NEXT_PUBLIC_*` key from `.env.example`. These are inlined at
   build time, so **changing one requires a rebuild**, not just a restart.

The build is a static export (`output: 'export'`, `trailingSlash: true`,
`images.unoptimized`). No SSR, no server actions, no route handlers — Pages serves files.

`npm run prebuild` copies MapLibre's worker into `public/`. MapLibre 6 loads it from
`new URL("./maplibre-gl-worker.mjs", import.meta.url)`, which webpack cannot analyse, so
no worker chunk is emitted and the map renders nothing at all — no error, just an empty
chart. The component calls `setWorkerUrl("/maplibre-gl-worker.mjs")` and the prebuild
step puts the file there. It is deliberately not committed: it is a build artefact of a
pinned dependency, and a stale copy would be a silent version skew.

## 5. Media

**Nothing to do.** All sixteen assets are in `frontend/public/media/` and ship with the
build. `backend/tests/test_media_assets.py` checks each one against
`frontend/src/lib/media-manifest.ts` for pixel size, byte budget and, for the two
videos, H.264 in yuv420p — so a missing or drifted asset fails the build rather than
falling back to a placeholder nobody notices in review.

To replace one, drop a file at the manifest's path at the manifest's size and rebuild;
no code change. `?slots=1` overlays each slot's id and size budget. To rebuild them all
from the product, run `frontend/scripts/make-media.mjs` — [Media Generation
Guide](./Media%20Generation%20Guide.md) explains how each was made and carries a
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
