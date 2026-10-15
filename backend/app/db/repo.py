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
        """Mirrors the database trigger: a new user gets an org and an owner membership."""
        with self._lock:
            existing = self.org_for_user(user_id)
            if existing:
                return existing
            org_id = uuid4()
            self.orgs[str(org_id)] = {
                "id": str(org_id),
                "name": "My organisation",
                "country": "AT",
                "plan": "free",
                "data_region": "frankfurt",
                "rulebase_pin": None,
                "created_at": _now(),
                "updated_at": _now(),
            }
            member = {"org_id": str(org_id), "user_id": str(user_id), "role": "owner", "created_at": _now()}
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
