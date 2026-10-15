"""Plan gating: the limits a free account actually hits, and the shape of the refusal.

Build spec §12 phase 8's Definition of Done is "a new user can sign up, run a
determination, and be blocked at the correct plan limit". These tests are that sentence,
checked. The other API modules set the plan to Pro so the feature under test is the
subject; here the plan *is* the subject.

Every refusal is a 402 with the feature, the limit, the usage and the plan that lifts it,
because the frontend renders the upgrade panel from those fields rather than from prose.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.services.plans import PLANS, plan_for
from tests.conftest import ALTA_X, make_token


def _drone(client: TestClient, auth: dict[str, str], name: str) -> Any:
    return client.post("/api/v1/drones", json={**ALTA_X, "name": name}, headers=auth)


def _operation(client: TestClient, auth: dict[str, str], name: str) -> Any:
    return client.post("/api/v1/operations", json={"name": name}, headers=auth)


def _problem(res: Any) -> dict[str, Any]:
    body = res.json()
    assert res.headers["content-type"].startswith("application/problem+json"), res.headers
    return dict(body)


# ------------------------------------------------------------------ the plan table


def test_a_new_signup_is_on_the_free_plan(signed_in: dict[str, Any]) -> None:
    assert signed_in["plan"] == "free"


def test_an_unknown_plan_in_the_database_falls_back_to_free_not_to_everything() -> None:
    """A rollback or a hand-edited row must withhold features, never grant them."""
    assert plan_for("enterprise").name == "free"
    assert plan_for(None).name == "free"
    assert plan_for("").name == "free"


def test_every_plan_name_the_database_allows_is_known_here() -> None:
    """The check constraint in migration 001 and this table must not drift apart."""
    import re
    from pathlib import Path

    sql = (Path(__file__).resolve().parent.parent / "app/db/migrations/001_init.sql").read_text()
    match = re.search(r"check \(plan in \(([^)]*)\)\)", sql)
    assert match, "could not find the plan check constraint in 001_init.sql"
    in_sql = {v.strip().strip("'") for v in match.group(1).split(",")}
    assert in_sql == set(PLANS), f"SQL allows {in_sql}, plans.py defines {set(PLANS)}"


# ------------------------------------------------------------------ counted limits


def test_the_free_fleet_limit_blocks_the_third_aircraft(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    limit = PLANS["free"].drones
    assert limit == 2
    for i in range(limit):
        assert _drone(client, auth, f"Aircraft {i}").status_code == 201

    res = _drone(client, auth, "One too many")
    assert res.status_code == 402
    body = _problem(res)
    assert body["code"] == "plan_limit"
    assert body["feature"] == "drones"
    assert body["limit"] == 2
    assert body["used"] == 2
    assert body["plan"] == "free"
    assert body["upgrade_to"] == "pro"


def test_the_free_operation_limit_blocks_the_fourth_operation(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    for i in range(PLANS["free"].operations or 0):
        assert _operation(client, auth, f"Operation {i}").status_code == 201
    res = _operation(client, auth, "One too many")
    assert res.status_code == 402
    assert _problem(res)["feature"] == "operations"


def test_pro_removes_the_fleet_limit(
    client: TestClient, auth: dict[str, str], pro: dict[str, Any]
) -> None:
    for i in range(5):
        assert _drone(client, auth, f"Aircraft {i}").status_code == 201, i


def test_a_determination_runs_on_the_free_plan_then_stops_at_the_allowance(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    """The DoD sentence: sign up, run a determination, be blocked at the right limit."""
    first = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert first.status_code == 200, first.text
    assert first.json()["sail"] == "III"

    # Re-running is idempotent and stores nothing new, so it does not consume the
    # allowance. Force a fresh run to the limit instead.
    from app.db import get_repo

    repo = get_repo()
    allowance = PLANS["free"].determinations_per_month or 0
    while repo.count_determinations_this_month(signed_org(client, auth)) < allowance:
        res = client.post(
            f"/api/v1/operations/{operation['id']}/determine?force=true", headers=auth
        )
        assert res.status_code == 200, res.text

    blocked = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert blocked.status_code == 402
    body = _problem(blocked)
    assert body["feature"] == "determinations"
    assert body["limit"] == allowance
    assert "this month" in body["title"]


def signed_org(client: TestClient, auth: dict[str, str]) -> str:
    return str(client.get("/api/v1/orgs/me", headers=auth).json()["id"])


# ------------------------------------------------------------------ feature gates


def test_the_counterfactual_advisor_is_refused_on_free_and_allowed_on_pro(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)

    refused = client.post(
        f"/api/v1/operations/{operation['id']}/counterfactual", json={"limit": 3}, headers=auth
    )
    assert refused.status_code == 402
    body = _problem(refused)
    assert body["feature"] == "counterfactuals"
    assert body["upgrade_to"] == "per_dossier"

    from app.db import get_repo

    get_repo().update_org(signed_org(client, auth), {"plan": "pro"})
    allowed = client.post(
        f"/api/v1/operations/{operation['id']}/counterfactual", json={"limit": 3}, headers=auth
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["suggestions"]


def test_conversational_intake_is_refused_on_free_and_says_the_form_still_works(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    res = client.post(
        f"/api/v1/operations/{operation['id']}/intake/chat",
        json={"text": "BVLOS along a powerline below 120 m."},
        headers=auth,
    )
    assert res.status_code == 402
    body = _problem(res)
    assert body["feature"] == "conversational_intake"
    assert "wizard" in body["detail"].lower() or "form" in body["detail"].lower()


def test_evidence_upload_is_refused_on_free(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    res = client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("survey.pdf", b"%PDF-1.7", "application/pdf")},
        headers=auth,
    )
    assert res.status_code == 402
    assert _problem(res)["feature"] == "evidence"


# ------------------------------------------------------------------ the dossier gate


def test_the_free_plan_can_read_the_determination_but_not_export_it(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    """The gate is on the export, not on the result. That distinction is the product."""
    run = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert run.status_code == 200
    assert run.json()["trace"], "the trace is readable on every plan"

    res = client.post(f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth)
    assert res.status_code == 402
    body = _problem(res)
    assert body["feature"] == "dossiers"
    assert body["upgrade_to"] == "per_dossier"


def test_a_dossier_credit_is_spent_by_one_export_and_then_gone(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    from app.db import get_repo

    repo = get_repo()
    org_id = signed_org(client, auth)
    client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    repo.update_org(org_id, {"plan": "per_dossier"})
    assert repo.grant_dossier_credits(org_id, 1) == 1

    first = client.post(f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth)
    assert first.status_code == 201, first.text
    assert int(repo.get_org(org_id)["dossier_credits"]) == 0

    second = client.post(f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth)
    assert second.status_code == 402
    assert "credit" in _problem(second)["title"].lower()


def test_a_failed_export_does_not_spend_a_credit(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    """No determination means no dossier — and the credit must survive that refusal."""
    from app.db import get_repo

    repo = get_repo()
    org_id = signed_org(client, auth)
    repo.update_org(org_id, {"plan": "per_dossier"})
    repo.grant_dossier_credits(org_id, 1)

    res = client.post(f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth)
    assert res.status_code == 409
    assert int(repo.get_org(org_id)["dossier_credits"]) == 1


# ------------------------------------------------------------------ ordering and leaks


def test_another_organisations_operation_is_404_not_402(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    """A 402 would confirm that the operation exists. Ownership is checked first."""
    stranger = {"Authorization": f"Bearer {make_token(uuid4())}"}
    client.post("/api/v1/auth/session", headers=stranger)
    for path, kwargs in [
        (f"/api/v1/operations/{operation['id']}/determine", {}),
        (f"/api/v1/operations/{operation['id']}/counterfactual", {"json": {"limit": 1}}),
        (f"/api/v1/operations/{operation['id']}/intake/chat", {"json": {"text": "x"}}),
        (f"/api/v1/operations/{operation['id']}/dossier", {"json": {}}),
        (
            f"/api/v1/operations/{operation['id']}/evidence",
            {"files": {"file": ("a.pdf", b"%PDF-1.7", "application/pdf")}},
        ),
    ]:
        res = client.post(path, headers=stranger, **kwargs)
        assert res.status_code == 404, f"{path} answered {res.status_code}"


def test_the_gate_never_runs_before_authentication(client: TestClient, operation: dict[str, Any]) -> None:
    res = client.post(f"/api/v1/operations/{operation['id']}/determine")
    assert res.status_code == 401


# ------------------------------------------------------------------ the billing state


def test_the_billing_state_reports_the_plan_its_limits_and_usage(
    client: TestClient, auth: dict[str, str], drone: dict[str, Any]
) -> None:
    res = client.get("/api/v1/billing", headers=auth)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["plan"]["name"] == "free"
    assert body["plan"]["limits"]["drones"] == 2
    assert body["plan"]["limits"]["counterfactuals"] is False
    assert body["usage"]["drones"] == 1
    assert body["usage"]["seats"] == 1
    assert body["dossier_credits"] == 0
    # No Stripe keys in the test environment, so nothing is purchasable and the UI is
    # told so rather than being allowed to offer a button that fails.
    assert body["billing_configured"] is False
    assert body["portal_available"] is False
    assert all(p["purchasable"] is False for p in body["plans"])
    assert {p["name"] for p in body["plans"]} == {"free", "per_dossier", "pro", "team"}


def test_an_unlimited_limit_is_null_not_a_large_number(
    client: TestClient, auth: dict[str, str], pro: dict[str, Any]
) -> None:
    body = client.get("/api/v1/billing", headers=auth).json()
    assert body["plan"]["name"] == "pro"
    assert body["plan"]["limits"]["drones"] is None
    assert body["plan"]["limits"]["determinations_per_month"] is None


def test_checkout_is_refused_without_stripe_keys(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    res = client.post("/api/v1/billing/checkout", json={"plan": "pro"}, headers=auth)
    assert res.status_code == 503
    body = _problem(res)
    assert body["code"] == "billing_unconfigured"
    assert "STRIPE_SECRET_KEY" in body["detail"]


def test_the_portal_is_refused_before_any_checkout(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    res = client.post("/api/v1/billing/portal", headers=auth)
    assert res.status_code == 409
    assert _problem(res)["code"] == "no_customer"


def test_a_member_cannot_start_a_purchase(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    from app.db import get_repo

    repo = get_repo()
    # Written on the stored row, not on the copy members() hands out: demotion is not
    # something the API exposes, so the test reaches for the store directly.
    for member in repo.org_members:  # type: ignore[attr-defined]
        member["role"] = "member"
    res = client.post("/api/v1/billing/checkout", json={"plan": "pro"}, headers=auth)
    assert res.status_code == 403
    assert _problem(res)["code"] == "forbidden"


def test_billing_needs_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/billing").status_code == 401
    assert client.post("/api/v1/billing/checkout", json={"plan": "pro"}).status_code == 401
