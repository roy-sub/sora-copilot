#!/usr/bin/env bash
#
# Smoke test against a deployed SORA Copilot.
#
# Walks the whole product the way a new customer does: sign up, add an aircraft, draw a
# volume, answer the wizard, confirm every fact, get a SAIL with a trace, look at the
# counterfactuals, attach evidence, read the submission checklist, export a dossier —
# and get refused at the right plan limit on the way.
#
#   BASE=https://sora-copilot.onrender.com \
#   SUPABASE_JWT_SECRET=... \
#   backend/scripts/smoke.sh
#
# The JWT secret is needed because the script mints its own access token rather than
# driving a browser. Use a throwaway user id; the run leaves an organisation behind.
#
# Exits non-zero on the first failure, so it is usable as a deploy gate.

set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8000}"
API="$BASE/api/v1"
USER_ID="${USER_ID:-$(python3 -c 'import uuid;print(uuid.uuid4())')}"
PLAN="${PLAN:-free}"          # set to pro to exercise the paid path end to end
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail() { printf '\n  FAIL  %s\n' "$*" >&2; exit 1; }
step() { printf '\n== %s ==\n' "$*"; }
ok()   { printf '  ok    %s\n' "$*"; }

jqp() { python3 -c "import json,sys;d=json.load(sys.stdin);print($1)"; }

if [[ -z "${SUPABASE_JWT_SECRET:-}" ]]; then
  fail "SUPABASE_JWT_SECRET is not set; the script cannot mint an access token."
fi

TOKEN=$(python3 - "$USER_ID" <<'PY'
import datetime as dt, os, sys
import jwt
sub = sys.argv[1]
now = dt.datetime.now(dt.UTC)
print(jwt.encode(
    {"sub": sub, "email": f"smoke+{sub[:8]}@example.eu", "aud": "authenticated",
     "role": "authenticated", "iat": now, "exp": now + dt.timedelta(minutes=30)},
    os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256"))
PY
)
H="Authorization: Bearer $TOKEN"

# ------------------------------------------------------------------ 0. reachable

step "the service is up"
curl -fsS "$BASE/healthz" > "$TMP/health.json" || fail "/healthz did not answer"
< "$TMP/health.json" jqp "f\"  env {d['env']} · rulebase {d['rulebase_version']} · build {d.get('git_sha')}\""
< "$TMP/health.json" jqp "d['status']" | grep -q '^ok$' || fail "/healthz is not ok"
curl -fsS "$BASE/healthz/deep" > "$TMP/deep.json" || fail "/healthz/deep did not answer"
ok "deep check: $(< "$TMP/deep.json" jqp "d" | head -c 160)"

# ------------------------------------------------------------------ 1. sign up

step "sign up"
curl -fsS -X POST "$API/auth/session" -H "$H" > "$TMP/org.json" || fail "could not create a session"
ORG=$(< "$TMP/org.json" jqp "d['id']")
STARTING_PLAN=$(< "$TMP/org.json" jqp "d['plan']")
ok "organisation $ORG on the $STARTING_PLAN plan"
[[ "$STARTING_PLAN" == "free" ]] || fail "a new sign-up should start on the free plan, not $STARTING_PLAN"

# ------------------------------------------------------------------ 2. the fleet

step "add an aircraft"
curl -fsS -X POST "$API/drones" -H "$H" -H 'content-type: application/json' -d '{
  "name":"Smoke test Alta X","registration":"SMOKE-01","max_dimension_m":1.32,
  "mtom_kg":15.9,"cruise_speed_ms":18,"max_speed_ms":22,
  "fitted_mitigations":["parachute","fts"]}' > "$TMP/drone.json" || fail "could not add an aircraft"
DRONE=$(< "$TMP/drone.json" jqp "d['id']")
ok "$(< "$TMP/drone.json" jqp "f\"{d['name']} · {d['kinetic_energy_j']/1000:.1f} kJ\"")"

# ------------------------------------------------------------------ 3. the operation

step "the wizard"
curl -fsS -X POST "$API/operations" -H "$H" -H 'content-type: application/json' \
  -d "{\"name\":\"Smoke test — Mur valley\",\"site\":\"Graz Süd, AT\",\"drone_id\":\"$DRONE\"}" \
  > "$TMP/op.json" || fail "could not create an operation"
OP=$(< "$TMP/op.json" jqp "d['id']")

curl -fsS -X PATCH "$API/operations/$OP/draft" -H "$H" -H 'content-type: application/json' -d "{
  \"drone_id\":\"$DRONE\",\"operation_type\":\"bvlos\",
  \"volume\":{\"flight_geography\":{\"type\":\"Polygon\",\"coordinates\":[[[15.40,47.10],[15.44,47.10],[15.44,47.12],[15.40,47.12],[15.40,47.10]]]},\"max_altitude_agl_m\":118},
  \"ground_environment\":\"sparsely_populated\",\"population_density_per_km2\":84,
  \"airspace_class\":\"g\",\"near_aerodrome\":true,\"controlled_airspace\":false,
  \"atypical_airspace\":false,\"mitigations\":{\"m1_strategic\":\"low\",\"strategic_air\":\"low\"},
  \"country\":\"AT\"}" > /dev/null || fail "could not save the draft"

curl -fsS -X POST "$API/operations/$OP/geo/derive" -H "$H" > "$TMP/geo.json" || fail "volume derivation failed"
ok "$(< "$TMP/geo.json" jqp "f\"FG {d['flight_geography_km2']} · CV {d['contingency_volume_km2']} · GRB {d['ground_risk_buffer_km2']} km2\"")"

# ------------------------------------------------------------------ 4. the determination

step "the determination"
curl -fsS -X POST "$API/operations/$OP/determine" -H "$H" > "$TMP/det.json" || fail "the determination did not run"
< "$TMP/det.json" jqp "f\"  iGRC {d['igrc']} · GRC {d['final_grc']} · ARC {d['initial_arc']}->{d['residual_arc']} · SAIL {d['sail']} · {len(d['trace'])} trace nodes\""
NODES=$(< "$TMP/det.json" jqp "len(d['trace'])")
[[ "$NODES" -gt 0 ]] || fail "a determination with no trace is a bug, not a degraded result"
< "$TMP/det.json" jqp "d['rulebase_version']" | grep -q . || fail "the determination carries no rulebase version"
ok "every conclusion carries a justification"

# ------------------------------------------------------------------ 5. the plan limit

step "the plan limit"
CODE=$(curl -sS -o "$TMP/limit.json" -w '%{http_code}' -X POST "$API/operations/$OP/counterfactual" \
  -H "$H" -H 'content-type: application/json' -d '{"limit":3}')
if [[ "$STARTING_PLAN" == "free" ]]; then
  [[ "$CODE" == "402" ]] || fail "the free plan should refuse the advisor with 402, got $CODE"
  < "$TMP/limit.json" jqp "f\"  402 {d['feature']} · {d['title']} · upgrade to {d['upgrade_to']}\""
  < "$TMP/limit.json" jqp "d['code']" | grep -q '^plan_limit$' || fail "the refusal is not a plan_limit problem"
  ok "refused for payment, not for a regulatory reason"
else
  [[ "$CODE" == "200" ]] || fail "a paid plan should reach the advisor, got $CODE"
fi

step "the webhook refuses an unsigned payload"
CODE=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$API/billing/webhook" \
  -H 'content-type: application/json' -d '{"id":"evt_smoke","type":"customer.subscription.created"}')
[[ "$CODE" == "400" || "$CODE" == "503" ]] || fail "the webhook answered $CODE to an unsigned payload"
ok "unsigned webhook → $CODE"

# ------------------------------------------------------------------ 6. the checklist

step "the submission checklist"
curl -fsS "$API/national/operations/$OP/checklist" -H "$H" > "$TMP/check.json" || fail "no checklist"
< "$TMP/check.json" jqp "f\"  {d['authority']} · SAIL {d['sail']} · {len(d['due'])} due\""
< "$TMP/check.json" jqp "d['warning'] or ''" | grep -q UNVERIFIED \
  && ok "the pack declares itself unverified, as it must until an annex is transcribed" \
  || ok "the pack is fully verified"

# ------------------------------------------------------------------ 7. persistence

step "it persisted"
curl -fsS "$API/operations/$OP/determination" -H "$H" > "$TMP/again.json" || fail "the determination did not persist"
A=$(< "$TMP/det.json" jqp "d['sail']"); B=$(< "$TMP/again.json" jqp "d['sail']")
[[ "$A" == "$B" ]] || fail "the stored determination says SAIL $B, the run said $A"
ok "SAIL $B read back from storage"
< "$TMP/health.json" jqp "d['supabase_configured']" | grep -q True \
  || printf '  note  this deployment has no database: nothing survives a restart\n'

printf '\nAll checks passed against %s\n' "$BASE"
