"""The Stripe webhook: the only unauthenticated write endpoint in the product.

Three properties carry the whole thing, and each is tested against a real signature
computed with Stripe's own scheme rather than a mocked verifier:

1. An unsigned, wrongly-signed or stale payload changes nothing.
2. A redelivery changes nothing — Stripe retries, and a second delivery must not grant a
   second month or a second credit.
3. A plan comes from a *configured* price id, so renaming a product in the Stripe
   dashboard cannot change what a customer is entitled to.

No network: `stripe.Webhook.construct_event` is pure signature verification, and nothing
in these paths calls Stripe's API.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

WEBHOOK_SECRET = "whsec_test_secret_padded_out_to_a_realistic_length_000"
PRICE_PRO = "price_pro_test"
PRICE_TEAM = "price_team_test"
PRICE_DOSSIER = "price_dossier_test"


@pytest.fixture
def stripe_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A deployment with Stripe configured, without any key that could reach Stripe."""
    from app.config import get_settings

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_not_a_real_key")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("STRIPE_PRICE_PRO", PRICE_PRO)
    monkeypatch.setenv("STRIPE_PRICE_TEAM", PRICE_TEAM)
    monkeypatch.setenv("STRIPE_PRICE_DOSSIER", PRICE_DOSSIER)
    monkeypatch.setenv("STRIPE_RETURN_URL", "https://app.example.eu/app/settings/")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def sign(payload: bytes, secret: str = WEBHOOK_SECRET, timestamp: int | None = None) -> str:
    """Stripe's `t=…,v1=…` header, computed the way Stripe computes it."""
    ts = timestamp if timestamp is not None else int(time.time())
    signature = hmac.new(
        secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return f"t={ts},v1={signature}"


def post_event(
    client: TestClient, event: dict[str, Any], *, secret: str = WEBHOOK_SECRET, timestamp: int | None = None
) -> Any:
    payload = json.dumps(event).encode()
    return client.post(
        "/api/v1/billing/webhook",
        content=payload,
        headers={"stripe-signature": sign(payload, secret, timestamp), "content-type": "application/json"},
    )


def subscription_event(
    org_id: str,
    *,
    event_id: str = "evt_sub_1",
    event_type: str = "customer.subscription.created",
    price: str = PRICE_PRO,
    status: str = "active",
    subscription_id: str = "sub_test_1",
    customer: str = "cus_test_1",
    period_end: int | None = None,
    cancel_at_period_end: bool = False,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "type": event_type,
        "created": int(time.time()),
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer,
                "status": status,
                "cancel_at_period_end": cancel_at_period_end,
                "metadata": {"org_id": org_id},
                "items": {
                    "data": [
                        {
                            "price": {"id": price},
                            "current_period_end": period_end or int(time.time()) + 30 * 86400,
                        }
                    ]
                },
            }
        },
    }


def checkout_event(
    org_id: str,
    *,
    event_id: str = "evt_cs_1",
    session_id: str = "cs_test_1",
    mode: str = "payment",
    payment_status: str = "paid",
    plan: str = "per_dossier",
    customer: str = "cus_test_1",
) -> dict[str, Any]:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": session_id,
                "mode": mode,
                "payment_status": payment_status,
                "customer": customer,
                "payment_intent": "pi_test_1",
                "amount_total": 14900,
                "currency": "eur",
                "client_reference_id": org_id,
                "metadata": {"org_id": org_id, "plan": plan},
            }
        },
    }


def org_of(client: TestClient, auth: dict[str, str]) -> str:
    return str(client.get("/api/v1/orgs/me", headers=auth).json()["id"])


def plan_of(org_id: str) -> str:
    from app.db import get_repo

    return str(get_repo().get_org(org_id)["plan"])


# ------------------------------------------------------------------ signature


def test_an_unsigned_webhook_is_refused_and_changes_nothing(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    org_id = org_of(client, auth)
    res = client.post(
        "/api/v1/billing/webhook",
        content=json.dumps(subscription_event(org_id)).encode(),
        headers={"content-type": "application/json"},
    )
    assert res.status_code == 400
    assert res.json()["code"] == "signature_invalid"
    assert plan_of(org_id) == "free"


def test_a_wrongly_signed_webhook_is_refused_and_changes_nothing(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    org_id = org_of(client, auth)
    res = post_event(client, subscription_event(org_id), secret="whsec_the_wrong_secret_entirely_0000")
    assert res.status_code == 400
    assert plan_of(org_id) == "free"


def test_a_stale_signature_is_refused(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    """Stripe's own tolerance window. A replayed payload from an hour ago is not valid."""
    org_id = org_of(client, auth)
    res = post_event(client, subscription_event(org_id), timestamp=int(time.time()) - 3600)
    assert res.status_code == 400
    assert plan_of(org_id) == "free"


def test_webhooks_are_refused_when_no_secret_is_configured(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    """Without a secret nothing can be verified, so nothing is trusted."""
    org_id = org_of(client, auth)
    res = post_event(client, subscription_event(org_id))
    assert res.status_code == 503
    assert res.json()["code"] == "billing_unconfigured"
    assert plan_of(org_id) == "free"


def test_the_webhook_needs_no_authentication_once_signed(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    """Stripe has no session. A valid signature is the whole credential."""
    org_id = org_of(client, auth)
    res = post_event(client, subscription_event(org_id))
    assert res.status_code == 200, res.text
    assert res.json() == {"received": True, "outcome": "applied"}


# ------------------------------------------------------------------ subscriptions


def test_a_subscription_moves_the_org_onto_the_plan_for_its_price(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    from app.db import get_repo

    org_id = org_of(client, auth)
    assert post_event(client, subscription_event(org_id)).status_code == 200
    assert plan_of(org_id) == "pro"

    org = get_repo().get_org(org_id)
    assert org["stripe_customer_id"] == "cus_test_1"
    assert org["stripe_subscription_id"] == "sub_test_1"
    assert org["plan_period_end"]

    # The subscription row records why, and is not what the request path reads.
    subs = get_repo().list_subscriptions(org_id)
    assert len(subs) == 1
    assert subs[0]["plan"] == "pro"
    assert subs[0]["status"] == "active"
    assert subs[0]["stripe_price_id"] == PRICE_PRO

    # And the gate now lets the paid feature through.
    assert client.get("/api/v1/billing", headers=auth).json()["plan"]["name"] == "pro"


def test_a_price_this_deployment_does_not_sell_changes_nothing(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    """Another product on the same Stripe account must not grant a plan here."""
    org_id = org_of(client, auth)
    res = post_event(client, subscription_event(org_id, price="price_someone_elses_product"))
    assert res.status_code == 200
    assert res.json()["outcome"] == "ignored"
    assert plan_of(org_id) == "free"


def test_the_plan_is_never_read_from_the_events_own_metadata(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    """A forged `metadata.plan` on a team price must not buy Consultancy."""
    org_id = org_of(client, auth)
    event = subscription_event(org_id, price=PRICE_TEAM)
    event["data"]["object"]["metadata"]["plan"] = "consultancy"
    assert post_event(client, event).status_code == 200
    assert plan_of(org_id) == "team"


def test_a_cancelled_subscription_returns_the_org_to_free(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    org_id = org_of(client, auth)
    post_event(client, subscription_event(org_id))
    assert plan_of(org_id) == "pro"

    cancelled = subscription_event(
        org_id, event_id="evt_sub_2", event_type="customer.subscription.deleted", status="canceled"
    )
    assert post_event(client, cancelled).status_code == 200
    assert plan_of(org_id) == "free"


def test_past_due_keeps_access_during_the_dunning_window(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    """A failed card must not strand an operator mid-application."""
    org_id = org_of(client, auth)
    post_event(client, subscription_event(org_id))
    event = subscription_event(
        org_id, event_id="evt_sub_3", event_type="customer.subscription.updated", status="past_due"
    )
    assert post_event(client, event).status_code == 200
    assert plan_of(org_id) == "pro"


def test_a_failed_invoice_alone_does_not_downgrade(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    org_id = org_of(client, auth)
    post_event(client, subscription_event(org_id))
    invoice = {
        "id": "evt_inv_1",
        "type": "invoice.payment_failed",
        "created": int(time.time()),
        "data": {"object": {"id": "in_1", "customer": "cus_test_1", "metadata": {"org_id": org_id}}},
    }
    assert post_event(client, invoice).status_code == 200
    assert plan_of(org_id) == "pro"


def test_a_cancelled_subscription_leaves_the_determinations_readable(
    client: TestClient,
    auth: dict[str, str],
    operation: dict[str, Any],
    complete_draft: dict[str, Any],
    stripe_env: None,
) -> None:
    """A compliance record outlives the subscription that produced it."""
    org_id = org_of(client, auth)
    post_event(client, subscription_event(org_id))
    run = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert run.status_code == 200, run.text

    post_event(
        client,
        subscription_event(
            org_id, event_id="evt_sub_9", event_type="customer.subscription.deleted", status="canceled"
        ),
    )
    assert plan_of(org_id) == "free"
    after = client.get(f"/api/v1/operations/{operation['id']}/determination", headers=auth)
    assert after.status_code == 200
    assert after.json()["sail"] == run.json()["sail"]
    assert after.json()["trace"]


# ------------------------------------------------------------------ idempotency


def test_a_redelivered_event_is_a_no_op(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    from app.db import get_repo

    org_id = org_of(client, auth)
    event = subscription_event(org_id)
    assert post_event(client, event).json()["outcome"] == "applied"
    again = post_event(client, event)
    assert again.status_code == 200
    assert again.json()["outcome"] == "duplicate"
    assert len(get_repo().list_subscriptions(org_id)) == 1


def test_a_redelivered_purchase_does_not_grant_a_second_credit(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    from app.db import get_repo

    org_id = org_of(client, auth)
    assert post_event(client, checkout_event(org_id)).json()["outcome"] == "applied"
    assert int(get_repo().get_org(org_id)["dossier_credits"]) == 1

    assert post_event(client, checkout_event(org_id)).json()["outcome"] == "duplicate"
    assert int(get_repo().get_org(org_id)["dossier_credits"]) == 1
    assert len(get_repo().list_purchases(org_id)) == 1


def test_an_event_with_no_id_is_refused_because_it_cannot_be_made_idempotent(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    org_id = org_of(client, auth)
    event = subscription_event(org_id)
    del event["id"]
    res = post_event(client, event)
    assert res.status_code == 422
    assert plan_of(org_id) == "free"


def test_an_unhandled_event_type_is_recorded_and_ignored(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    org_id = org_of(client, auth)
    event = {
        "id": "evt_other_1",
        "type": "customer.discount.created",
        "created": int(time.time()),
        "data": {"object": {"id": "di_1", "metadata": {"org_id": org_id}}},
    }
    assert post_event(client, event).json()["outcome"] == "ignored"
    # Recorded nonetheless, so a redelivery is still cheap.
    assert post_event(client, event).json()["outcome"] == "duplicate"


# ------------------------------------------------------------------ attribution


def test_an_event_naming_no_organisation_changes_nothing(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    org_id = org_of(client, auth)
    event = subscription_event(org_id, customer="cus_unknown")
    event["data"]["object"]["metadata"] = {}
    res = post_event(client, event)
    assert res.status_code == 200
    assert res.json()["outcome"] == "ignored"
    assert plan_of(org_id) == "free"


def test_an_event_naming_another_organisation_does_not_touch_this_one(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    from tests.conftest import make_token

    mine = org_of(client, auth)
    other_auth = {"Authorization": f"Bearer {make_token(uuid4())}"}
    client.post("/api/v1/auth/session", headers=other_auth)
    theirs = org_of(client, other_auth)
    assert mine != theirs

    assert post_event(client, subscription_event(theirs)).status_code == 200
    assert plan_of(theirs) == "pro"
    assert plan_of(mine) == "free"


def test_an_event_naming_an_organisation_that_does_not_exist_is_ignored(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    org_id = org_of(client, auth)
    event = subscription_event(str(UUID(int=0)), customer="cus_nobody")
    res = post_event(client, event)
    assert res.status_code == 200
    assert res.json()["outcome"] == "ignored"
    assert plan_of(org_id) == "free"


# ------------------------------------------------------------------ purchases


def test_a_one_off_purchase_grants_a_credit_and_the_pay_as_you_go_plan(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    from app.db import get_repo

    org_id = org_of(client, auth)
    assert post_event(client, checkout_event(org_id)).json()["outcome"] == "applied"
    org = get_repo().get_org(org_id)
    assert int(org["dossier_credits"]) == 1
    assert org["plan"] == "per_dossier"
    purchase = get_repo().list_purchases(org_id)[0]
    assert purchase["credits"] == 1
    assert purchase["amount_cents"] == 14900
    assert purchase["currency"] == "eur"


def test_a_credit_purchase_never_demotes_a_subscriber(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    from app.db import get_repo

    org_id = org_of(client, auth)
    post_event(client, subscription_event(org_id))
    assert plan_of(org_id) == "pro"
    post_event(client, checkout_event(org_id))
    assert plan_of(org_id) == "pro"
    assert int(get_repo().get_org(org_id)["dossier_credits"]) == 1


def test_an_unpaid_checkout_session_grants_nothing(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    from app.db import get_repo

    org_id = org_of(client, auth)
    res = post_event(client, checkout_event(org_id, payment_status="unpaid"))
    assert res.json()["outcome"] == "ignored"
    assert int(get_repo().get_org(org_id)["dossier_credits"]) == 0


def test_a_subscription_checkout_does_not_also_grant_a_credit(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    """The subscription events set the plan. Doing it twice would be two truths."""
    from app.db import get_repo

    org_id = org_of(client, auth)
    res = post_event(client, checkout_event(org_id, mode="subscription", plan="pro"))
    assert res.json()["outcome"] == "ignored"
    assert int(get_repo().get_org(org_id)["dossier_credits"]) == 0
    # But the customer id is remembered, so the billing portal works afterwards.
    assert get_repo().get_org(org_id)["stripe_customer_id"] == "cus_test_1"


def test_the_portal_becomes_available_once_stripe_knows_the_customer(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    before = client.get("/api/v1/billing", headers=auth).json()
    assert before["portal_available"] is False
    post_event(client, subscription_event(org_of(client, auth)))
    after = client.get("/api/v1/billing", headers=auth).json()
    assert after["billing_configured"] is True
    assert after["portal_available"] is True
    assert after["status"] == "active"


# ------------------------------------------------------------------ checkout


def test_checkout_refuses_a_plan_with_no_price_configured(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import get_settings

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_not_a_real_key")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.delenv("STRIPE_PRICE_TEAM", raising=False)
    get_settings.cache_clear()
    try:
        res = client.post("/api/v1/billing/checkout", json={"plan": "team"}, headers=auth)
        assert res.status_code == 503
        assert "STRIPE_PRICE_TEAM" in res.json()["detail"]
    finally:
        get_settings.cache_clear()


def test_a_return_path_cannot_redirect_off_site(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], stripe_env: None
) -> None:
    """An open redirect in a payment flow is how a confirmation lands on a phishing page."""
    res = client.post(
        "/api/v1/billing/checkout",
        json={"plan": "pro", "success_path": "https://evil.example.com/thanks"},
        headers=auth,
    )
    assert res.status_code == 422
    assert res.json()["code"] == "validation_failed"


def test_the_return_path_resolves_against_the_configured_origin(stripe_env: None) -> None:
    from app.api.v1.billing import _return_url
    from app.config import get_settings

    settings = get_settings()
    assert _return_url(settings, "/app/settings/?checkout=done") == (
        "https://app.example.eu/app/settings/?checkout=done"
    )
    # A path without its leading slash still cannot escape the origin.
    assert _return_url(settings, "app/x").startswith("https://app.example.eu/")
