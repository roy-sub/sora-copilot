"""The production data layer, against Supabase Postgres.

Mirrors ``MemoryRepo`` exactly, so every API test that passes against the in-memory store
describes behaviour this class must also provide. Org scoping is applied in every query
that touches an org-owned table; the service-role key bypasses row-level security, so
these filters are the authorisation boundary, not a convenience.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.db.client import get_client
from app.db.repo import Id, NotFound, Row


def _month_start() -> datetime:
    """The boundary a monthly allowance is measured from. UTC, first of the month."""
    return datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _is_duplicate_key(exc: Exception) -> bool:
    """Whether a Supabase/PostgREST error is a unique-violation rather than a real fault.

    Matched on Postgres' own SQLSTATE where the client exposes it, falling back to the
    message. A misread here would either drop a legitimate event or apply a duplicate
    one, so both the code and the text are checked.
    """
    code = getattr(exc, "code", None)
    if str(code) == "23505":
        return True
    message = f"{getattr(exc, 'message', '')} {exc}".lower()
    return "duplicate key" in message or "23505" in message


def _one(rows: list[Row] | None, what: str) -> Row:
    if not rows:
        raise NotFound(what)
    return rows[0]


class SupabaseRepo:
    """Durable storage. Every method is org-scoped by an id taken from a verified JWT."""

    @property
    def is_durable(self) -> bool:
        return True

    @property
    def _db(self) -> Any:
        return get_client()

    # -------------------------------------------------------------- orgs

    def org_for_user(self, user_id: Id) -> Row | None:
        res = self._db.table("org_members").select("*").eq("user_id", str(user_id)).limit(1).execute()
        return _one(res.data, "unreachable") if res.data else None

    def ensure_org_for_user(self, user_id: Id, email: str | None) -> Row:
        """The database trigger normally does this on sign-up; this is the backstop.

        A user who signed up before the trigger existed, or whose org was deleted, would
        otherwise be stuck on a dead dashboard with no way to create anything.
        """
        existing = self.org_for_user(user_id)
        if existing:
            return existing
        org = self._db.table("orgs").insert({"name": "My organisation", "country": "AT"}).execute()
        org_id = org.data[0]["id"]
        member = (
            self._db.table("org_members")
            .insert({"org_id": org_id, "user_id": str(user_id), "role": "owner"})
            .execute()
        )
        return _one(member.data, "org_members insert returned nothing")

    def get_org(self, org_id: Id) -> Row:
        res = self._db.table("orgs").select("*").eq("id", str(org_id)).limit(1).execute()
        return _one(res.data, f"org {org_id}")

    def update_org(self, org_id: Id, patch: Row) -> Row:
        clean = {k: v for k, v in patch.items() if v is not None}
        if not clean:
            return self.get_org(org_id)
        res = self._db.table("orgs").update(clean).eq("id", str(org_id)).execute()
        return _one(res.data, f"org {org_id}")

    def members(self, org_id: Id) -> list[Row]:
        res = self._db.table("org_members").select("*").eq("org_id", str(org_id)).execute()
        return list(res.data or [])

    # -------------------------------------------------------------- drones

    def list_drones(self, org_id: Id) -> list[Row]:
        res = self._db.table("drones").select("*").eq("org_id", str(org_id)).order("created_at").execute()
        return list(res.data or [])

    def get_drone(self, org_id: Id, drone_id: Id) -> Row:
        res = (
            self._db.table("drones")
            .select("*")
            .eq("org_id", str(org_id))
            .eq("id", str(drone_id))
            .limit(1)
            .execute()
        )
        return _one(res.data, f"drone {drone_id}")

    def create_drone(self, org_id: Id, data: Row) -> Row:
        # kinetic_energy_j is a generated column; sending it would be rejected.
        payload = {k: v for k, v in data.items() if k != "kinetic_energy_j"}
        res = self._db.table("drones").insert({**payload, "org_id": str(org_id)}).execute()
        return _one(res.data, "drone insert returned nothing")

    def update_drone(self, org_id: Id, drone_id: Id, patch: Row) -> Row:
        clean = {k: v for k, v in patch.items() if v is not None and k != "kinetic_energy_j"}
        if not clean:
            return self.get_drone(org_id, drone_id)
        res = (
            self._db.table("drones").update(clean).eq("org_id", str(org_id)).eq("id", str(drone_id)).execute()
        )
        return _one(res.data, f"drone {drone_id}")

    def delete_drone(self, org_id: Id, drone_id: Id) -> None:
        res = self._db.table("drones").delete().eq("org_id", str(org_id)).eq("id", str(drone_id)).execute()
        _one(res.data, f"drone {drone_id}")

    # -------------------------------------------------------------- operations

    def list_operations(self, org_id: Id) -> list[Row]:
        res = (
            self._db.table("operations")
            .select("*")
            .eq("org_id", str(org_id))
            .order("created_at", desc=True)
            .execute()
        )
        return list(res.data or [])

    def get_operation(self, org_id: Id, operation_id: Id) -> Row:
        res = (
            self._db.table("operations")
            .select("*")
            .eq("org_id", str(org_id))
            .eq("id", str(operation_id))
            .limit(1)
            .execute()
        )
        return _one(res.data, f"operation {operation_id}")

    def create_operation(self, org_id: Id, data: Row) -> Row:
        res = self._db.table("operations").insert({**data, "org_id": str(org_id)}).execute()
        return _one(res.data, "operation insert returned nothing")

    def update_operation(self, org_id: Id, operation_id: Id, patch: Row) -> Row:
        clean = {k: v for k, v in patch.items() if v is not None}
        if not clean:
            return self.get_operation(org_id, operation_id)
        res = (
            self._db.table("operations")
            .update(clean)
            .eq("org_id", str(org_id))
            .eq("id", str(operation_id))
            .execute()
        )
        return _one(res.data, f"operation {operation_id}")

    def delete_operation(self, org_id: Id, operation_id: Id) -> None:
        res = (
            self._db.table("operations")
            .delete()
            .eq("org_id", str(org_id))
            .eq("id", str(operation_id))
            .execute()
        )
        _one(res.data, f"operation {operation_id}")

    # -------------------------------------------------------------- proposed facts

    def list_facts(self, operation_id: Id) -> list[Row]:
        res = (
            self._db.table("proposed_facts")
            .select("*")
            .eq("operation_id", str(operation_id))
            .order("created_at")
            .execute()
        )
        return list(res.data or [])

    def add_facts(self, operation_id: Id, facts: list[Row]) -> list[Row]:
        if not facts:
            return []
        payload = [{**f, "operation_id": str(operation_id), "status": "pending"} for f in facts]
        res = self._db.table("proposed_facts").insert(payload).execute()
        return list(res.data or [])

    def set_fact_status(self, operation_id: Id, fact_id: Id, status: str, user_id: Id) -> Row:
        res = (
            self._db.table("proposed_facts")
            .update(
                {
                    "status": status,
                    "confirmed_by": str(user_id),
                    "confirmed_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("operation_id", str(operation_id))
            .eq("id", str(fact_id))
            .execute()
        )
        return _one(res.data, f"fact {fact_id}")

    def clear_facts(self, operation_id: Id) -> None:
        self._db.table("proposed_facts").delete().eq("operation_id", str(operation_id)).execute()

    # -------------------------------------------------------------- geo

    def put_geo_facts(self, operation_id: Id, data: Row) -> Row:
        # Append-only: a determination pins the raster version it sampled, so an older
        # sample has to remain readable.
        res = self._db.table("geo_facts").insert({**data, "operation_id": str(operation_id)}).execute()
        return _one(res.data, "geo_facts insert returned nothing")

    def get_geo_facts(self, operation_id: Id) -> Row | None:
        res = (
            self._db.table("geo_facts")
            .select("*")
            .eq("operation_id", str(operation_id))
            .order("sampled_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    # -------------------------------------------------------------- determinations

    def find_determination(self, operation_id: Id, mission_hash: str, rulebase: str) -> Row | None:
        res = (
            self._db.table("determinations")
            .select("*")
            .eq("operation_id", str(operation_id))
            .eq("mission_hash", mission_hash)
            .eq("rulebase_version", rulebase)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def latest_determination(self, operation_id: Id) -> Row | None:
        res = (
            self._db.table("determinations")
            .select("*")
            .eq("operation_id", str(operation_id))
            .order("computed_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def create_determination(self, data: Row) -> Row:
        res = self._db.table("determinations").insert(data).execute()
        return _one(res.data, "determination insert returned nothing")

    # -------------------------------------------------------------- mitigations

    def replace_mitigations(self, operation_id: Id, rows: list[Row]) -> list[Row]:
        self._db.table("mitigations").delete().eq("operation_id", str(operation_id)).execute()
        if not rows:
            return []
        payload = [{**r, "operation_id": str(operation_id)} for r in rows]
        res = self._db.table("mitigations").insert(payload).execute()
        return list(res.data or [])

    def list_mitigations(self, operation_id: Id) -> list[Row]:
        res = self._db.table("mitigations").select("*").eq("operation_id", str(operation_id)).execute()
        return list(res.data or [])

    # -------------------------------------------------------------- evidence

    def list_evidence(self, operation_id: Id) -> list[Row]:
        res = (
            self._db.table("evidence_files")
            .select("*")
            .eq("operation_id", str(operation_id))
            .order("uploaded_at")
            .execute()
        )
        return list(res.data or [])

    def add_evidence(self, operation_id: Id, data: Row) -> Row:
        res = self._db.table("evidence_files").insert({**data, "operation_id": str(operation_id)}).execute()
        return _one(res.data, "evidence insert returned nothing")

    def delete_evidence(self, operation_id: Id, evidence_id: Id) -> None:
        res = (
            self._db.table("evidence_files")
            .delete()
            .eq("operation_id", str(operation_id))
            .eq("id", str(evidence_id))
            .execute()
        )
        _one(res.data, f"evidence {evidence_id}")

    # -------------------------------------------------------------- dossiers

    def list_dossiers(self, operation_id: Id) -> list[Row]:
        res = (
            self._db.table("dossiers")
            .select("*")
            .eq("operation_id", str(operation_id))
            .order("version", desc=True)
            .execute()
        )
        return list(res.data or [])

    def add_dossier(self, operation_id: Id, data: Row) -> Row:
        res = self._db.table("dossiers").insert({**data, "operation_id": str(operation_id)}).execute()
        return _one(res.data, "dossier insert returned nothing")

    def next_dossier_version(self, operation_id: Id) -> int:
        res = (
            self._db.table("dossiers")
            .select("version")
            .eq("operation_id", str(operation_id))
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        return (int(res.data[0]["version"]) + 1) if res.data else 1

    # -------------------------------------------------------------- llm accounting

    def count_llm_calls_this_month(self, org_id: Id) -> int:
        start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        res = (
            self._db.table("llm_calls")
            .select("id", count="exact")
            .eq("org_id", str(org_id))
            .gte("created_at", start.isoformat())
            .execute()
        )
        return int(res.count or 0)

    def log_llm_call(self, org_id: Id, data: Row) -> Row:
        res = self._db.table("llm_calls").insert({**data, "org_id": str(org_id)}).execute()
        return _one(res.data, "llm_calls insert returned nothing")

    # -------------------------------------------------------------- plan accounting

    def _operation_ids(self, org_id: Id) -> list[str]:
        res = self._db.table("operations").select("id").eq("org_id", str(org_id)).execute()
        return [str(row["id"]) for row in (res.data or [])]

    def _count(self, table: str, org_id: Id) -> int:
        res = self._db.table(table).select("id", count="exact").eq("org_id", str(org_id)).execute()
        return int(res.count or 0)

    def count_drones(self, org_id: Id) -> int:
        return self._count("drones", org_id)

    def count_operations(self, org_id: Id) -> int:
        return self._count("operations", org_id)

    def count_evidence(self, org_id: Id) -> int:
        ids = self._operation_ids(org_id)
        if not ids:
            return 0
        res = (
            self._db.table("evidence_files")
            .select("id", count="exact")
            .in_("operation_id", ids)
            .execute()
        )
        return int(res.count or 0)

    def _count_since_month_start(self, table: str, column: str, org_id: Id) -> int:
        ids = self._operation_ids(org_id)
        if not ids:
            return 0
        res = (
            self._db.table(table)
            .select("id", count="exact")
            .in_("operation_id", ids)
            .gte(column, _month_start().isoformat())
            .execute()
        )
        return int(res.count or 0)

    def count_determinations_this_month(self, org_id: Id) -> int:
        return self._count_since_month_start("determinations", "computed_at", org_id)

    def count_dossiers_this_month(self, org_id: Id) -> int:
        return self._count_since_month_start("dossiers", "generated_at", org_id)

    # -------------------------------------------------------------- billing

    def spend_dossier_credit(self, org_id: Id) -> bool:
        """Decrement one credit, atomically, or report that there was none.

        ``dossier_credits`` carries a ``>= 0`` check constraint (migration 002), so a
        conditional update that would go negative is rejected by the database rather
        than by a read-then-write in this process. Two concurrent exports cannot both
        spend the last credit.
        """
        current = int(self.get_org(org_id).get("dossier_credits") or 0)
        if current <= 0:
            return False
        res = (
            self._db.table("orgs")
            .update({"dossier_credits": current - 1})
            .eq("id", str(org_id))
            .eq("dossier_credits", current)  # optimistic: fails if another export won
            .execute()
        )
        return bool(res.data)

    def grant_dossier_credits(self, org_id: Id, credits: int) -> int:
        current = int(self.get_org(org_id).get("dossier_credits") or 0)
        res = (
            self._db.table("orgs")
            .update({"dossier_credits": current + int(credits)})
            .eq("id", str(org_id))
            .execute()
        )
        return int(_one(res.data, "orgs update returned nothing")["dossier_credits"])

    def org_for_stripe_customer(self, customer_id: str) -> Row | None:
        res = (
            self._db.table("orgs")
            .select("*")
            .eq("stripe_customer_id", customer_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def upsert_subscription(self, org_id: Id, data: Row) -> Row:
        res = (
            self._db.table("subscriptions")
            .upsert({**data, "org_id": str(org_id)}, on_conflict="stripe_subscription_id")
            .execute()
        )
        return _one(res.data, "subscriptions upsert returned nothing")

    def list_subscriptions(self, org_id: Id) -> list[Row]:
        res = (
            self._db.table("subscriptions")
            .select("*")
            .eq("org_id", str(org_id))
            .order("created_at", desc=True)
            .execute()
        )
        return list(res.data or [])

    def record_purchase(self, org_id: Id, data: Row) -> Row:
        res = (
            self._db.table("dossier_purchases")
            .upsert({**data, "org_id": str(org_id)}, on_conflict="stripe_session_id")
            .execute()
        )
        return _one(res.data, "dossier_purchases upsert returned nothing")

    def list_purchases(self, org_id: Id) -> list[Row]:
        res = (
            self._db.table("dossier_purchases")
            .select("*")
            .eq("org_id", str(org_id))
            .order("created_at", desc=True)
            .execute()
        )
        return list(res.data or [])

    def remember_stripe_event(self, event_id: str, data: Row) -> bool:
        """Insert the event id. False means Stripe has sent this one before.

        A plain insert, not an upsert: the primary key is what makes the second delivery
        fail, and that failure is the answer. Catching the conflict is how this stays
        correct without a transaction the REST client cannot open.
        """
        try:
            self._db.table("stripe_events").insert({**data, "id": event_id}).execute()
        except Exception as exc:  # the client raises its own error types, not one we can name
            if _is_duplicate_key(exc):
                return False
            raise
        return True

    # -------------------------------------------------------------- rulebase

    def current_rulebase(self) -> Row | None:
        res = self._db.table("rulebase_versions").select("*").eq("is_current", True).limit(1).execute()
        return res.data[0] if res.data else None

    def upsert_rulebase(self, data: Row) -> Row:
        res = self._db.table("rulebase_versions").upsert(data, on_conflict="version").execute()
        return _one(res.data, "rulebase upsert returned nothing")


def new_id() -> str:
    return str(uuid4())
