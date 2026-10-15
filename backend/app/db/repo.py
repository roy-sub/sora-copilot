"""The data layer, behind one interface.

Two implementations:

* ``SupabaseRepo`` — production, against Supabase Postgres.
* ``MemoryRepo`` — an in-process store used by the tests **and** when Supabase is not
  configured, so the whole application runs locally with no account, no keys and no
  network. That is not a toy: the API, the wizard, the engine and the dossier builder all
  work against it, which means the product can be reviewed end to end before anyone
  provisions anything. It says so in ``/healthz`` and in the UI, and everything is lost
  when the process stops.

Nothing here knows about FastAPI, and nothing here reaches the engine. Org scoping is
applied by every method that takes an ``org_id``; the value always comes from a verified
JWT via ``app.deps``, never from a request body.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

Row = dict[str, Any]

#: Ids travel as UUIDs inside the app and as strings in stored rows. Accepting both at
#: every boundary is what stops the two stores disagreeing about what an id is.
Id = UUID | str


def _month_start() -> str:
    """The first of the current month, UTC, as an ISO string — monthly allowances key on it."""
    return (
        datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    )


def _now() -> str:
    return datetime.now(UTC).isoformat()


class NotFound(LookupError):
    """The row does not exist, or belongs to another organisation.

    Deliberately one error for both: telling a caller that a row exists but is not theirs
    leaks the existence of other organisations' operations.
    """


class Repo(Protocol):
    """Everything the API needs from storage."""

    # -------------------------------------------------------------- orgs
    def org_for_user(self, user_id: Id) -> Row | None: ...
    def get_org(self, org_id: Id) -> Row: ...
    def update_org(self, org_id: Id, patch: Row) -> Row: ...
    def members(self, org_id: Id) -> list[Row]: ...
    def set_member_role(self, org_id: Id, user_id: Id, role: str) -> Row: ...
    def remove_member(self, org_id: Id, user_id: Id) -> None: ...

    # -------------------------------------------------------------- invitations
    def list_invites(self, org_id: Id) -> list[Row]: ...
    def create_invite(self, org_id: Id, data: Row) -> Row: ...
    def delete_invite(self, org_id: Id, invite_id: Id) -> None: ...
    def pending_invite_for(self, email: str) -> Row | None: ...
    def accept_invite(self, invite_id: Id, user_id: Id) -> Row: ...
    def ensure_org_for_user(self, user_id: Id, email: str | None) -> Row: ...

    # -------------------------------------------------------------- drones
    def list_drones(self, org_id: Id) -> list[Row]: ...
    def get_drone(self, org_id: Id, drone_id: Id) -> Row: ...
    def create_drone(self, org_id: Id, data: Row) -> Row: ...
    def update_drone(self, org_id: Id, drone_id: Id, patch: Row) -> Row: ...
    def delete_drone(self, org_id: Id, drone_id: Id) -> None: ...

    # -------------------------------------------------------------- operations
    def list_operations(self, org_id: Id) -> list[Row]: ...
    def get_operation(self, org_id: Id, operation_id: Id) -> Row: ...
    def create_operation(self, org_id: Id, data: Row) -> Row: ...
    def update_operation(self, org_id: Id, operation_id: Id, patch: Row) -> Row: ...
    def delete_operation(self, org_id: Id, operation_id: Id) -> None: ...

    # -------------------------------------------------------------- proposed facts
    def list_facts(self, operation_id: Id) -> list[Row]: ...
    def add_facts(self, operation_id: Id, facts: list[Row]) -> list[Row]: ...
    def set_fact_status(
        self, operation_id: Id, fact_id: Id, status: str, user_id: Id
    ) -> Row: ...
    def clear_facts(self, operation_id: Id) -> None: ...

    # -------------------------------------------------------------- geo
    def put_geo_facts(self, operation_id: Id, data: Row) -> Row: ...
    def get_geo_facts(self, operation_id: Id) -> Row | None: ...

    # -------------------------------------------------------------- determinations
    def find_determination(
        self, operation_id: Id, mission_hash: str, rulebase: str
    ) -> Row | None: ...
    def latest_determination(self, operation_id: Id) -> Row | None: ...
    def create_determination(self, data: Row) -> Row: ...

    # -------------------------------------------------------------- mitigations
    def replace_mitigations(self, operation_id: Id, rows: list[Row]) -> list[Row]: ...
    def list_mitigations(self, operation_id: Id) -> list[Row]: ...

    # -------------------------------------------------------------- evidence
    def list_evidence(self, operation_id: Id) -> list[Row]: ...
    def add_evidence(self, operation_id: Id, data: Row) -> Row: ...
    def delete_evidence(self, operation_id: Id, evidence_id: Id) -> None: ...

    # -------------------------------------------------------------- dossiers
    def list_dossiers(self, operation_id: Id) -> list[Row]: ...
    def add_dossier(self, operation_id: Id, data: Row) -> Row: ...
    def next_dossier_version(self, operation_id: Id) -> int: ...

    # -------------------------------------------------------------- llm accounting
    def count_llm_calls_this_month(self, org_id: Id) -> int: ...
    def log_llm_call(self, org_id: Id, data: Row) -> Row: ...

    # -------------------------------------------------------------- plan accounting
    def count_drones(self, org_id: Id) -> int: ...
    def count_operations(self, org_id: Id) -> int: ...
    def count_evidence(self, org_id: Id) -> int: ...
    def count_determinations_this_month(self, org_id: Id) -> int: ...
    def count_dossiers_this_month(self, org_id: Id) -> int: ...

    # -------------------------------------------------------------- billing
    def spend_dossier_credit(self, org_id: Id) -> bool: ...
    def grant_dossier_credits(self, org_id: Id, credits: int) -> int: ...
    def org_for_stripe_customer(self, customer_id: str) -> Row | None: ...
    def upsert_subscription(self, org_id: Id, data: Row) -> Row: ...
    def list_subscriptions(self, org_id: Id) -> list[Row]: ...
    def record_purchase(self, org_id: Id, data: Row) -> Row: ...
    def list_purchases(self, org_id: Id) -> list[Row]: ...
    def remember_stripe_event(self, event_id: str, data: Row) -> bool: ...

    # -------------------------------------------------------------- rulebase
    def current_rulebase(self) -> Row | None: ...
    def upsert_rulebase(self, data: Row) -> Row: ...

    # -------------------------------------------------------------- meta
    @property
    def is_durable(self) -> bool:
        """False for the in-memory store, so the UI can say data will not survive."""
        ...


class MemoryRepo:
    """In-process storage. Thread-safe, ordered, and deliberately not durable."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Keyed by the STRING form of each id, matching what SupabaseRepo returns, so
        # neither store can disagree with the other about what an id is.
        self.orgs: dict[str, Row] = {}
        self.org_members: list[Row] = []
        self.invites: dict[str, Row] = {}
        self.drones: dict[str, Row] = {}
        self.operations: dict[str, Row] = {}
        self.facts: dict[str, Row] = {}
        self.geo: dict[str, Row] = {}
        self.determinations: dict[str, Row] = {}
        self.mitigations: dict[str, Row] = {}
        self.evidence: dict[str, Row] = {}
        self.dossiers: dict[str, Row] = {}
        self.llm_calls: list[Row] = []
        self.rulebases: dict[str, Row] = {}
        self.subscriptions: dict[str, Row] = {}
        self.purchases: dict[str, Row] = {}
        #: Stripe event ids already applied. The webhook's memory, so a redelivery is a
        #: no-op rather than a second month of credits.
        self.stripe_events: dict[str, Row] = {}

    @property
    def is_durable(self) -> bool:
        return False

    # -------------------------------------------------------------- helpers

    def _own_operation(self, org_id: Id | str, operation_id: Id | str) -> Row:
        row = self.operations.get(str(operation_id))
        if row is None or row["org_id"] != str(org_id):
            raise NotFound(f"operation {operation_id}")
        return row

    # -------------------------------------------------------------- orgs

    def org_for_user(self, user_id: Id) -> Row | None:
        with self._lock:
            for m in self.org_members:
                if m["user_id"] == str(user_id):
                    return deepcopy(m)
        return None

    def ensure_org_for_user(self, user_id: Id, email: str | None) -> Row:
        """A new user joins the organisation that invited them, or gets their own.

        The invitation is matched on the email in the **verified** JWT, so it can only be
        claimed by someone who has proved control of that address to Supabase Auth. See
        migration 003 for why there is no token link.
        """
        with self._lock:
            existing = self.org_for_user(user_id)
            if existing:
                return existing

            invite = self.pending_invite_for(email) if email else None
            if invite is not None:
                member = {
                    "org_id": str(invite["org_id"]),
                    "user_id": str(user_id),
                    "role": str(invite.get("role") or "member"),
                    "email": email,
                    "created_at": _now(),
                }
                self.org_members.append(member)
                self.accept_invite(invite["id"], user_id)
                return deepcopy(member)

            org_id = uuid4()
            self.orgs[str(org_id)] = {
                "id": str(org_id),
                "name": "My organisation",
                "country": "AT",
                "plan": "free",
                "data_region": "frankfurt",
                "rulebase_pin": None,
                # Mirrors migration 002's defaults, so a caller never has to tell the
                # two stores apart by which keys are present.
                "dossier_credits": 0,
                "stripe_customer_id": None,
                "stripe_subscription_id": None,
                "plan_period_end": None,
                "created_at": _now(),
                "updated_at": _now(),
            }
            member = {
                "org_id": str(org_id),
                "user_id": str(user_id),
                "role": "owner",
                "email": email,
                "created_at": _now(),
            }
            self.org_members.append(member)
            return deepcopy(member)

    def get_org(self, org_id: Id) -> Row:
        with self._lock:
            row = self.orgs.get(str(org_id))
            if row is None:
                raise NotFound(f"org {org_id}")
            return deepcopy(row)

    def update_org(self, org_id: Id, patch: Row) -> Row:
        with self._lock:
            row = self.orgs.get(str(org_id))
            if row is None:
                raise NotFound(f"org {org_id}")
            row.update({k: v for k, v in patch.items() if v is not None})
            row["updated_at"] = _now()
            return deepcopy(row)

    def set_member_role(self, org_id: Id, user_id: Id, role: str) -> Row:
        with self._lock:
            for m in self.org_members:
                if m["org_id"] == str(org_id) and m["user_id"] == str(user_id):
                    m["role"] = role
                    return deepcopy(m)
        raise NotFound(f"member {user_id}")

    def remove_member(self, org_id: Id, user_id: Id) -> None:
        with self._lock:
            before = len(self.org_members)
            self.org_members = [
                m
                for m in self.org_members
                if not (m["org_id"] == str(org_id) and m["user_id"] == str(user_id))
            ]
            if len(self.org_members) == before:
                raise NotFound(f"member {user_id}")

    # -------------------------------------------------------------- invitations

    def list_invites(self, org_id: Id) -> list[Row]:
        with self._lock:
            rows = [i for i in self.invites.values() if i["org_id"] == str(org_id)]
            return [
                deepcopy(i) for i in sorted(rows, key=lambda i: str(i["created_at"]), reverse=True)
            ]

    def create_invite(self, org_id: Id, data: Row) -> Row:
        """Invite an address, or update the pending invitation it already has.

        Mirrors the partial unique index in migration 003: a second invitation to the
        same address is the same invitation with a new role, not a duplicate row.
        """
        email = str(data["email"]).strip().lower()
        with self._lock:
            for existing in self.invites.values():
                if (
                    existing["org_id"] == str(org_id)
                    and existing["email"] == email
                    and existing.get("accepted_at") is None
                ):
                    existing.update({k: v for k, v in data.items() if k != "email"})
                    return deepcopy(existing)
            invite_id = uuid4()
            row = {
                **data,
                "id": str(invite_id),
                "org_id": str(org_id),
                "email": email,
                "created_at": _now(),
                "accepted_at": None,
                "accepted_by": None,
            }
            self.invites[str(invite_id)] = row
            return deepcopy(row)

    def delete_invite(self, org_id: Id, invite_id: Id) -> None:
        with self._lock:
            row = self.invites.get(str(invite_id))
            if row is None or row["org_id"] != str(org_id):
                raise NotFound(f"invite {invite_id}")
            del self.invites[str(invite_id)]

    def pending_invite_for(self, email: str) -> Row | None:
        """The oldest unclaimed, unexpired invitation for an address, if any."""
        wanted = email.strip().lower()
        now = _now()
        with self._lock:
            candidates = [
                i
                for i in self.invites.values()
                if i["email"] == wanted
                and i.get("accepted_at") is None
                and str(i.get("expires_at") or "9999") > now
            ]
            if not candidates:
                return None
            return deepcopy(min(candidates, key=lambda i: str(i["created_at"])))

    def accept_invite(self, invite_id: Id, user_id: Id) -> Row:
        """Mark an invitation claimed. Kept, not deleted: who let this person in, and when."""
        with self._lock:
            row = self.invites.get(str(invite_id))
            if row is None:
                raise NotFound(f"invite {invite_id}")
            row["accepted_at"] = _now()
            row["accepted_by"] = str(user_id)
            return deepcopy(row)

    def members(self, org_id: Id) -> list[Row]:
        with self._lock:
            return [deepcopy(m) for m in self.org_members if m["org_id"] == str(org_id)]

    # -------------------------------------------------------------- drones

    def list_drones(self, org_id: Id) -> list[Row]:
        with self._lock:
            rows = [d for d in self.drones.values() if d["org_id"] == str(org_id)]
            return [deepcopy(d) for d in sorted(rows, key=lambda d: d["created_at"])]

    def get_drone(self, org_id: Id, drone_id: Id) -> Row:
        with self._lock:
            row = self.drones.get(str(drone_id))
            if row is None or row["org_id"] != str(org_id):
                raise NotFound(f"drone {drone_id}")
            return deepcopy(row)

    def create_drone(self, org_id: Id, data: Row) -> Row:
        with self._lock:
            drone_id = str(data.get("id") or uuid4())
            row = {
                **data,
                "id": drone_id,
                "org_id": str(org_id),
                "created_at": _now(),
                "updated_at": _now(),
            }
            # Generated in Postgres; computed here so both stores agree.
            row["kinetic_energy_j"] = 0.5 * float(row["mtom_kg"]) * float(row["max_speed_ms"]) ** 2
            self.drones[str(drone_id)] = row
            return deepcopy(row)

    def update_drone(self, org_id: Id, drone_id: Id, patch: Row) -> Row:
        with self._lock:
            row = self.get_drone(org_id, drone_id)
            row.update({k: v for k, v in patch.items() if v is not None})
            row["kinetic_energy_j"] = 0.5 * float(row["mtom_kg"]) * float(row["max_speed_ms"]) ** 2
            row["updated_at"] = _now()
            self.drones[str(drone_id)] = row
            return deepcopy(row)

    def delete_drone(self, org_id: Id, drone_id: Id) -> None:
        with self._lock:
            self.get_drone(org_id, drone_id)
            del self.drones[str(drone_id)]

    # -------------------------------------------------------------- operations

    def list_operations(self, org_id: Id) -> list[Row]:
        with self._lock:
            rows = [o for o in self.operations.values() if o["org_id"] == str(org_id)]
            return [deepcopy(o) for o in sorted(rows, key=lambda o: o["created_at"], reverse=True)]

    def get_operation(self, org_id: Id, operation_id: Id) -> Row:
        with self._lock:
            return deepcopy(self._own_operation(org_id, operation_id))

    def create_operation(self, org_id: Id, data: Row) -> Row:
        with self._lock:
            op_id = str(data.get("id") or uuid4())
            row = {
                "status": "draft",
                "mission": {},
                **data,
                "id": op_id,
                "org_id": str(org_id),
                "created_at": _now(),
                "updated_at": _now(),
            }
            self.operations[str(op_id)] = row
            return deepcopy(row)

    def update_operation(self, org_id: Id, operation_id: Id, patch: Row) -> Row:
        with self._lock:
            row = self._own_operation(org_id, operation_id)
            for key, value in patch.items():
                if value is not None:
                    row[key] = value
            row["updated_at"] = _now()
            return deepcopy(row)

    def delete_operation(self, org_id: Id, operation_id: Id) -> None:
        with self._lock:
            self._own_operation(org_id, operation_id)
            del self.operations[str(operation_id)]
            # Cascade, as the foreign keys do in Postgres.
            for store in (self.facts, self.determinations, self.mitigations, self.evidence, self.dossiers):
                for key in [k for k, v in store.items() if v.get("operation_id") == str(operation_id)]:
                    del store[key]
            self.geo.pop(str(operation_id), None)

    # -------------------------------------------------------------- proposed facts

    def list_facts(self, operation_id: Id) -> list[Row]:
        with self._lock:
            rows = [f for f in self.facts.values() if f["operation_id"] == str(operation_id)]
            return [deepcopy(f) for f in sorted(rows, key=lambda f: f["created_at"])]

    def add_facts(self, operation_id: Id, facts: list[Row]) -> list[Row]:
        with self._lock:
            out = []
            for f in facts:
                fact_id = uuid4()
                row = {
                    **f,
                    "id": str(fact_id),
                    "operation_id": str(operation_id),
                    "status": "pending",
                    "confirmed_by": None,
                    "confirmed_at": None,
                    "created_at": _now(),
                }
                self.facts[str(fact_id)] = row
                out.append(deepcopy(row))
            return out

    def set_fact_status(
        self, operation_id: Id, fact_id: Id, status: str, user_id: Id
    ) -> Row:
        with self._lock:
            row = self.facts.get(str(fact_id))
            if row is None or row["operation_id"] != str(operation_id):
                raise NotFound(f"fact {fact_id}")
            row["status"] = status
            # Mirrors the database check: a decision must name who made it.
            row["confirmed_by"] = str(user_id)
            row["confirmed_at"] = _now()
            return deepcopy(row)

    def clear_facts(self, operation_id: Id) -> None:
        with self._lock:
            for key in [k for k, v in self.facts.items() if v["operation_id"] == str(operation_id)]:
                del self.facts[key]

    # -------------------------------------------------------------- geo

    def put_geo_facts(self, operation_id: Id, data: Row) -> Row:
        with self._lock:
            row = {**data, "id": str(uuid4()), "operation_id": str(operation_id), "sampled_at": _now()}
            self.geo[str(operation_id)] = row
            return deepcopy(row)

    def get_geo_facts(self, operation_id: Id) -> Row | None:
        with self._lock:
            row = self.geo.get(str(operation_id))
            return deepcopy(row) if row else None

    # -------------------------------------------------------------- determinations

    def find_determination(self, operation_id: Id, mission_hash: str, rulebase: str) -> Row | None:
        with self._lock:
            for row in self.determinations.values():
                if (
                    row["operation_id"] == str(operation_id)
                    and row["mission_hash"] == mission_hash
                    and row["rulebase_version"] == rulebase
                ):
                    return deepcopy(row)
        return None

    def latest_determination(self, operation_id: Id) -> Row | None:
        with self._lock:
            rows = [d for d in self.determinations.values() if d["operation_id"] == str(operation_id)]
            if not rows:
                return None
            return deepcopy(max(rows, key=lambda d: d["computed_at"]))

    def create_determination(self, data: Row) -> Row:
        with self._lock:
            det_id = str(data["id"])
            row = {**data, "id": det_id}
            self.determinations[str(det_id)] = row
            return deepcopy(row)

    # -------------------------------------------------------------- mitigations

    def replace_mitigations(self, operation_id: Id, rows: list[Row]) -> list[Row]:
        """One writer. The mission JSON is authoritative; this table is its projection."""
        with self._lock:
            for key in [k for k, v in self.mitigations.items() if v["operation_id"] == str(operation_id)]:
                del self.mitigations[key]
            out = []
            for r in rows:
                mid = uuid4()
                row = {**r, "id": str(mid), "operation_id": str(operation_id), "created_at": _now()}
                self.mitigations[str(mid)] = row
                out.append(deepcopy(row))
            return out

    def list_mitigations(self, operation_id: Id) -> list[Row]:
        with self._lock:
            return [deepcopy(m) for m in self.mitigations.values() if m["operation_id"] == str(operation_id)]

    # -------------------------------------------------------------- evidence

    def list_evidence(self, operation_id: Id) -> list[Row]:
        with self._lock:
            rows = [e for e in self.evidence.values() if e["operation_id"] == str(operation_id)]
            return [deepcopy(e) for e in sorted(rows, key=lambda e: e["uploaded_at"])]

    def add_evidence(self, operation_id: Id, data: Row) -> Row:
        with self._lock:
            eid = uuid4()
            row = {**data, "id": str(eid), "operation_id": str(operation_id), "uploaded_at": _now()}
            self.evidence[str(eid)] = row
            return deepcopy(row)

    def delete_evidence(self, operation_id: Id, evidence_id: Id) -> None:
        with self._lock:
            row = self.evidence.get(str(evidence_id))
            if row is None or row["operation_id"] != str(operation_id):
                raise NotFound(f"evidence {evidence_id}")
            del self.evidence[str(evidence_id)]

    # -------------------------------------------------------------- dossiers

    def list_dossiers(self, operation_id: Id) -> list[Row]:
        with self._lock:
            rows = [d for d in self.dossiers.values() if d["operation_id"] == str(operation_id)]
            return [deepcopy(d) for d in sorted(rows, key=lambda d: d["version"], reverse=True)]

    def add_dossier(self, operation_id: Id, data: Row) -> Row:
        with self._lock:
            did = uuid4()
            row = {**data, "id": str(did), "operation_id": str(operation_id), "generated_at": _now()}
            self.dossiers[str(did)] = row
            return deepcopy(row)

    def next_dossier_version(self, operation_id: Id) -> int:
        with self._lock:
            rows = [d for d in self.dossiers.values() if d["operation_id"] == str(operation_id)]
            return max((int(d["version"]) for d in rows), default=0) + 1

    # -------------------------------------------------------------- llm accounting

    def count_llm_calls_this_month(self, org_id: Id) -> int:
        start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        with self._lock:
            return sum(1 for c in self.llm_calls if c["org_id"] == str(org_id) and c["created_at"] >= start)

    def log_llm_call(self, org_id: Id, data: Row) -> Row:
        with self._lock:
            row = {**data, "id": str(uuid4()), "org_id": str(org_id), "created_at": _now()}
            self.llm_calls.append(row)
            return deepcopy(row)

    # -------------------------------------------------------------- plan accounting

    def count_drones(self, org_id: Id) -> int:
        with self._lock:
            return sum(1 for d in self.drones.values() if d["org_id"] == str(org_id))

    def count_operations(self, org_id: Id) -> int:
        with self._lock:
            return sum(1 for o in self.operations.values() if o["org_id"] == str(org_id))

    def _own_operation_ids(self, org_id: Id) -> set[str]:
        return {o["id"] for o in self.operations.values() if o["org_id"] == str(org_id)}

    def count_evidence(self, org_id: Id) -> int:
        with self._lock:
            mine = self._own_operation_ids(org_id)
            return sum(1 for e in self.evidence.values() if e["operation_id"] in mine)

    def count_determinations_this_month(self, org_id: Id) -> int:
        start = _month_start()
        with self._lock:
            mine = self._own_operation_ids(org_id)
            return sum(
                1
                for d in self.determinations.values()
                if d["operation_id"] in mine and str(d.get("computed_at", "")) >= start
            )

    def count_dossiers_this_month(self, org_id: Id) -> int:
        start = _month_start()
        with self._lock:
            mine = self._own_operation_ids(org_id)
            return sum(
                1
                for d in self.dossiers.values()
                if d["operation_id"] in mine and str(d.get("generated_at", "")) >= start
            )

    # -------------------------------------------------------------- billing

    def spend_dossier_credit(self, org_id: Id) -> bool:
        """Decrement if there is one to spend. Returns whether a credit was taken.

        Check-then-decrement under the lock, so two concurrent exports cannot both see
        the last credit.
        """
        with self._lock:
            org = self.orgs.get(str(org_id))
            if org is None:
                raise NotFound("org")
            credits = int(org.get("dossier_credits") or 0)
            if credits <= 0:
                return False
            org["dossier_credits"] = credits - 1
            return True

    def grant_dossier_credits(self, org_id: Id, credits: int) -> int:
        with self._lock:
            org = self.orgs.get(str(org_id))
            if org is None:
                raise NotFound("org")
            org["dossier_credits"] = int(org.get("dossier_credits") or 0) + int(credits)
            return int(org["dossier_credits"])

    def org_for_stripe_customer(self, customer_id: str) -> Row | None:
        with self._lock:
            for org in self.orgs.values():
                if org.get("stripe_customer_id") == customer_id:
                    return deepcopy(org)
        return None

    def upsert_subscription(self, org_id: Id, data: Row) -> Row:
        key = str(data["stripe_subscription_id"])
        with self._lock:
            existing = self.subscriptions.get(key, {})
            row = {
                **existing,
                **data,
                "id": existing.get("id", str(uuid4())),
                "org_id": str(org_id),
                "created_at": existing.get("created_at", _now()),
                "updated_at": _now(),
            }
            self.subscriptions[key] = row
            return deepcopy(row)

    def list_subscriptions(self, org_id: Id) -> list[Row]:
        with self._lock:
            rows = [s for s in self.subscriptions.values() if s["org_id"] == str(org_id)]
            return [deepcopy(s) for s in sorted(rows, key=lambda s: str(s["created_at"]), reverse=True)]

    def record_purchase(self, org_id: Id, data: Row) -> Row:
        key = str(data["stripe_session_id"])
        with self._lock:
            if key in self.purchases:
                return deepcopy(self.purchases[key])
            row = {**data, "id": str(uuid4()), "org_id": str(org_id), "created_at": _now()}
            self.purchases[key] = row
            return deepcopy(row)

    def list_purchases(self, org_id: Id) -> list[Row]:
        with self._lock:
            rows = [p for p in self.purchases.values() if p["org_id"] == str(org_id)]
            return [deepcopy(p) for p in sorted(rows, key=lambda p: str(p["created_at"]), reverse=True)]

    def remember_stripe_event(self, event_id: str, data: Row) -> bool:
        """Record an event id. False means it was already applied, so skip it.

        Claiming the id *before* the handler runs is deliberate: a handler that fails
        half-way must not be retried blindly against state it already changed. The
        webhook returns 200 and the failure is logged, because Stripe retries on
        non-2xx and a retry would hit the same partial state.
        """
        with self._lock:
            if event_id in self.stripe_events:
                return False
            self.stripe_events[event_id] = {**data, "id": event_id, "applied_at": _now()}
            return True

    # -------------------------------------------------------------- rulebase

    def current_rulebase(self) -> Row | None:
        with self._lock:
            for row in self.rulebases.values():
                if row.get("is_current"):
                    return deepcopy(row)
        return None

    def upsert_rulebase(self, data: Row) -> Row:
        with self._lock:
            version = str(data["version"])
            if data.get("is_current"):
                for row in self.rulebases.values():
                    row["is_current"] = False
            row = {**self.rulebases.get(version, {}), **data, "released_at": _now()}
            self.rulebases[version] = row
            return deepcopy(row)
