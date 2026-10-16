# Third Party Setup Guide

Everything you have to go and get, where to get it, and which line of `.env` it fills.

Work top to bottom. The product runs with **none** of this configured — it says
"unconfigured" instead of failing — so you can stop at any point and still have a
working deployment, just a smaller one.

| # | Service | Needed for | Cost | Time |
|---|---|---|---|---|
| 1 | [Supabase](https://supabase.com) | Sign-in, the database, file storage | Free tier | ~15 min |
| 2 | [Anthropic](https://console.anthropic.com) | Conversational intake, dossier prose | Pay as you go, capped | ~5 min |
| 3 | [Stripe](https://dashboard.stripe.com) | Taking money | Free + per-transaction | ~20 min |
| 4 | [Render](https://render.com) | Hosting the backend | Free tier | ~10 min |
| 5 | [Cloudflare Pages](https://pages.cloudflare.com) | Hosting the frontend | Free tier | ~10 min |
| 6 | A map style URL | The basemap under the volume editor | Free options exist | ~5 min |
| 7 | [UptimeRobot](https://uptimerobot.com) *(optional)* | Keeping the free backend awake | Free tier | ~3 min |

Copy `.env.example` to `backend/.env` and `frontend/.env.local` before you start. What
each variable does, and what you lose by leaving it blank, is in
[ENV Example](./ENV%20Example.md) — this page is about where the values come from.

> **The one rule.** `SUPABASE_SERVICE_ROLE_KEY` and `STRIPE_SECRET_KEY` bypass every
> security control they touch. They belong in the backend's environment and nowhere
> else — never in the frontend, never in the repository, never in a screenshot. Anything
> prefixed `NEXT_PUBLIC_` is compiled into the JavaScript the browser downloads, so
> treat those as published the moment you build.

---

## 1. Supabase — sign-in, database, storage

**Go to:** https://supabase.com → New project.

Pick an **EU region** (Frankfurt or Dublin). EU data residency is one of the things this
product sells, and the region cannot be changed after the project is created.

### What to collect

| Where in the dashboard | Copy | Goes into |
|---|---|---|
| Project Settings → Data API → Project URL | `https://abcdefgh.supabase.co` | `SUPABASE_URL` **and** `NEXT_PUBLIC_SUPABASE_URL` |
| Project Settings → API Keys → `anon` `public` | a long `eyJ…` string | `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| Project Settings → API Keys → `service_role` `secret` | a long `eyJ…` string | `SUPABASE_SERVICE_ROLE_KEY` |
| Project Settings → JWT Keys (JWT Secret) | a ~40-character string | `SUPABASE_JWT_SECRET` |

The anon key is *meant* to be public and is constrained by row-level security. The
service-role key is not: it bypasses RLS entirely, which is why the backend holds it and
the browser never does.

### Then do these four things

1. **Run the migrations.** SQL Editor → New query → paste and run, in this order:
   - `backend/app/db/migrations/001_init.sql`
   - `backend/app/db/migrations/002_billing.sql`
   - `backend/app/db/migrations/003_invites.sql`

   001 creates every table with RLS on, the storage buckets, and the
   trigger that gives each new user an organisation. 002 adds subscriptions, dossier
   credits and the webhook's idempotency log. 003 adds invitations, so a Team plan's
   seats can be used. Never edit a migration that has been applied; corrections land as
   the next number.

2. **Enable email auth.** Authentication → Sign In / Providers → Email. Turn on email,
   and turn on magic links if you want passwordless sign-in (the sign-in form offers
   both).

3. **Add the redirect URLs.** Authentication → URL Configuration → Redirect URLs:
   ```
   http://localhost:3000/app/
   https://<your-pages-domain>/app/
   ```
   Magic links fail *silently* without this. It is the single most common setup mistake.

4. **No email sender is needed.** Inviting a colleague does not send a message: the
   invitation is claimed on first sign-in by the address in their verified Supabase
   token. The owner invites an address and tells their colleague to sign up with it.
   That is deliberate — there is no link to forward, leak or replay, and no sixth
   third-party service to configure.

5. **Check the buckets exist.** Storage should list `evidence`, `dossiers` and
   `public-assets`. The first two are private; the backend mints 15-minute signed URLs
   for them and the browser never gets a durable link.

### Things that will bite you later

- **The free tier pauses a project after about 7 days with no traffic.** Restore it from
  the dashboard; it takes a few minutes and loses nothing. `/healthz` deliberately stays
  green while it is paused — `/healthz/deep` is the one that reports the database.
- **Free tier storage is 1 GB.** Evidence files are capped at 40 MB each, so that is
  roughly 25 worst-case uploads. Watch it before you invite real operators.

---

## 2. Anthropic — conversational intake and dossier prose

**Go to:** https://console.anthropic.com → API Keys → Create key.

| Copy | Goes into |
|---|---|
| `sk-ant-…` | `ANTHROPIC_API_KEY` |

Leave `ANTHROPIC_MODEL` at its default unless you have a reason to change it.

**What it is used for, and what it is not.** The language model turns prose into
*candidate facts* that you confirm, and turns engine output into readable sentences. It
never decides anything: ground risk class, air risk class, SAIL, OSOs, robustness and
containment are computed by the clingo rules engine and only by the clingo rules engine.
That is enforced structurally — the module that calls Anthropic has no import path to
the module that writes determinations, and a test fails if one ever appears.

**Without a key** the product falls back to a deterministic regex extractor and says so
in the panel ("deterministic"). The wizard's form collects the same facts either way, so
this is a degraded experience rather than a broken one.

**Cost control.** `LLM_MONTHLY_CALL_CAP` (default 500) is checked *before* each call and
counted per organisation per month. Set a billing limit in the Anthropic console too —
belt and braces.

---

## 3. Stripe — taking money

Skip this entirely if you are not charging yet. With no `STRIPE_SECRET_KEY` the plan
panel says payments are not configured, and with no `STRIPE_WEBHOOK_SECRET` the webhook
endpoint refuses every request rather than trusting an unverified payload. Set **both or
neither**: a checkout whose webhook cannot be verified would take money and never grant
the plan.

**Stay in Test mode** until you have run a full checkout end to end.

### 3.1 The API key

**Developers → API keys → Secret key.**

| Copy | Goes into |
|---|---|
| `sk_test_…` (or `sk_live_…`) | `STRIPE_SECRET_KEY` |

### 3.2 The products and prices

**Product catalogue → Add product.** Create three:

| Product | Price | Billing | Fills |
|---|---|---|---|
| SORA Copilot Pro | €89 | Recurring, monthly | `STRIPE_PRICE_PRO` |
| SORA Copilot Team | €249 | Recurring, monthly | `STRIPE_PRICE_TEAM` |
| SORA Copilot — one dossier | €149 | One-off | `STRIPE_PRICE_DOSSIER` |

Copy the **price** id, which starts with `price_`. Not the product id, which starts with
`prod_` and will not work.

A plan is derived from the configured price id and from nothing else — never from the
product's name, never from event metadata. So you can rename anything in the Stripe
dashboard without changing what a customer is entitled to, and a forged `plan` field in
an event body buys nothing.

### 3.3 The webhook

**Developers → Webhooks → Add endpoint.**

- **Endpoint URL:** `https://<your-render-host>/api/v1/billing/webhook`
- **Events to send** — exactly these five, and no others:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_failed`

| Copy | Goes into |
|---|---|
| Signing secret, `whsec_…` | `STRIPE_WEBHOOK_SECRET` |

Every payload is verified against this secret before a single field is read, and every
event id is recorded before its handler runs — so a redelivery (Stripe *will* redeliver)
is a no-op rather than a second month of credits.

### 3.4 The customer portal

**Settings → Billing → Customer portal.** Turn it on, and allow customers to cancel and
to update their payment method. `POST /api/v1/billing/portal` sends them there rather
than rebuilding card forms and cancellation flows, which is both safer and less work.

### 3.5 The return URL

| Set | To |
|---|---|
| `STRIPE_RETURN_URL` | Your **frontend** origin plus the settings path, e.g. `https://sora-copilot.pages.dev/app/settings/` |

The checkout endpoint only ever takes a *path* from the caller and resolves it against
this origin, so a request cannot redirect a payment confirmation to someone else's page.

### 3.6 Test it before taking real money

```bash
stripe login
stripe listen --forward-to localhost:8000/api/v1/billing/webhook
# in another terminal
stripe trigger customer.subscription.created
```

Then check `GET /api/v1/billing` reports the new plan, and that replaying the same event
answers `{"outcome": "duplicate"}`.

---

## 4. Render — the backend

**Go to:** https://render.com → New → Web Service → connect the repository.

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Runtime | Python 3 |
| Build command | `pip install .` |
| Start command | `python main.py --prod` |
| Region | Frankfurt |
| Instance type | Free |
| Health check path | `/healthz` |

Set **every backend variable** from `.env.example` in Render's Environment tab, plus:

- `ENV=production` — the app refuses to start without the Supabase keys, which is what
  you want in production.
- `CORS_ORIGINS=https://<your-pages-domain>` — the frontend's origin, comma-separated if
  there is more than one.
- `GIT_SHA` — Render exposes the commit as `RENDER_GIT_COMMIT`; map it across so
  `/healthz` can be traced back to a build.

There is **no Dockerfile**: the build is `pip install .` and the start command is
`python main.py --prod`. Nothing needs apt-get — PDFs render through fpdf2 and the map
chart through Pillow, both pure Python, and the typeface ships in the repository.

**The free instance sleeps after ~15 minutes** and takes tens of seconds to wake. The
frontend already treats 502/503/504 and network failures as *warming* rather than errors
and says "the determination service is waking", so this is a slow first request, not a
broken one. Step 7 below reduces how often it happens.

---

## 5. Cloudflare Pages — the frontend

**Go to:** https://pages.cloudflare.com → Create a project → connect the repository.

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npm run build` |
| Output directory | `out` |

Set the five `NEXT_PUBLIC_*` variables:

```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_URL            # https://<your-render-host>
NEXT_PUBLIC_SITE_URL           # https://<your-pages-domain>
NEXT_PUBLIC_MAP_STYLE_URL      # step 6, optional
```

These are inlined at build time, so **changing one needs a rebuild**, not a restart.

Then go back to Supabase and add `https://<your-pages-domain>/app/` to the redirect URLs
if you have not already.

---

Not using Cloudflare? The frontend is a folder of static files, so any host will serve it — Hostinger included. [Deployment Guide](./Deployment%20Guide.md), Part Two, has the commands that produce the folder and what to do with it.

## 6. A map style URL — the basemap

**Optional.** Without it the volume editor still works: it draws on a plain graticule and
says the basemap is not configured. The geometry, the derived volumes and the
determination are completely unaffected — the basemap is an aid to drawing, not an input.

You need a **MapLibre-compatible style JSON URL**. Options, cheapest first:

- **A keyless public style.** Some providers publish free demo styles. Read their terms
  before putting one in production; "demo" usually means "not for production".
- **[MapTiler](https://www.maptiler.com)** — free tier, generous for this use.
  Maps → pick a style → Use vector style → copy the URL, which includes `?key=…`.
- **[Stadia Maps](https://stadiamaps.com)** — free tier, similar shape.
- **Self-hosted** — if you already run a tile server, point at its style JSON.

| Copy | Goes into |
|---|---|
| The style JSON URL | `NEXT_PUBLIC_MAP_STYLE_URL` |

Note that this one **is** public: it is compiled into the frontend bundle. If your
provider's key is in the URL, restrict it by HTTP referrer in their dashboard.

---

## 7. UptimeRobot — keeping the backend awake *(optional)*

**Go to:** https://uptimerobot.com → Add New Monitor.

| Setting | Value |
|---|---|
| Monitor type | HTTP(s) |
| URL | `https://<your-render-host>/healthz` |
| Interval | 5 minutes |

`/healthz` has no dependencies — it does not touch the database — so this is a cheap ping
that keeps the free instance warm during working hours. Use `/healthz/deep` for an
alerting monitor if you want to know when the *database* is unreachable, but do not poll
it every five minutes.

---

## Checking it all worked

```bash
# The backend is up and knows which build it is.
curl -s https://<render-host>/healthz | jq

# The database is reachable.
curl -s https://<render-host>/healthz/deep | jq     # expect database: ok

# The engine answers without an account.
curl -s -X POST https://<render-host>/api/v1/public/category-check \
  -H 'content-type: application/json' \
  -d '{"mass_band":"4to25","ground_environment":"sparsely_populated","operation_type":"bvlos"}' | jq

# The webhook refuses an unsigned payload. Anything but 400 is a serious problem.
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://<render-host>/api/v1/billing/webhook \
  -H 'content-type: application/json' -d '{"id":"x","type":"customer.subscription.created"}'
```

Or run the whole walkthrough:

```bash
BASE=https://<render-host> SUPABASE_JWT_SECRET=<the secret> backend/scripts/smoke.sh
```

Then in a browser: sign up, add an aircraft, draw a volume, answer the wizard, confirm
the facts, get a SAIL with a readable derivation tree, look at the counterfactuals,
export the DOCX, and reopen the operation to check it persisted.

---

## What is *still* missing after all of this

Configuring every service above gives you a working product that people can sign up to,
use, and pay for. One thing remains, and it cannot be bought.

**The Austria pack is this project's reading of the process, not a transcription of
anything Austro Control published.** Every one of its 14 items is marked UNVERIFIED in
the UI and in the dossier's Appendix C, and each says where to check it. Deliberately,
no item quotes a fee, a lead time or a sum insured — a plausible-looking number in a
compliance product is worse than an honest gap. The file to fill in is
`backend/app/national/packs/at.json`; set an item's `provenance` to `official` and its
`source` to the clause once you have confirmed it.

The pack is an operator's *checklist for their authority*, not part of the risk
determination: nothing in it can change an iGRC, a GRC, an ARC, a SAIL, an OSO or a
containment level, which is why the product is submittable without it.

**The regulatory tables are done.** All fourteen are transcribed from the EASA *Easy
Access Rules for Unmanned Aircraft Systems*, revision of June 2026, which carries the
SORA 2.5 AMC adopted by ED Decision 2025/018/R, with a page number on every one. No
determination carries an UNVERIFIED warning and the dossier no longer prints the
"must not be submitted" cover. `GET /api/v1/rulebase/current` reports the live state,
and the settings screen shows the same list.
[Final Manual Task](./Final%20Manual%20Task.md) records what that transcription changed —
four corrections move a verdict, so read it before you demonstrate the app to anyone who
saw the old numbers.

Nothing else on this page is outstanding: once the credentials above are in place, every
feature the product offers is live.
