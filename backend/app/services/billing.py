"""The only module that talks to Stripe.

Isolated for the same reason ``llm.py`` is: everything a third party controls enters the
product through one file, and that file can reach nothing that writes a determination.
``plans.py`` holds what a plan means; this holds how one is bought. The import direction
is one way — this module imports ``plans``, never the reverse — so plan limits can be
read on a deployment with no Stripe keys at all.

Two things here are load-bearing and easy to get wrong:

**Signature verification.** The webhook payload is attacker-controlled until
``stripe.Webhook.construct_event`` has verified it against the endpoint secret. Nothing
reads a field before that call. A deployment with no webhook secret refuses webhooks
rather than trusting them.

**Idempotency.** Stripe redelivers. Every handler is driven by an event id the caller
has already claimed in the database, so a redelivery does nothing rather than granting
a second month.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import stripe

from app.config import Settings
from app.services.plans import PLANS, PlanName

#: Events worth acting on. Anything else is recorded and ignored, because a webhook that
#: branches on an event it does not understand is a webhook that will misread one.
HANDLED = frozenset(
    {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_failed",
    }
)

#: Stripe statuses that mean the plan is live. `past_due` keeps access during the
#: dunning window: cutting a compliance tool off mid-application over a failed card is
#: a worse failure than a few days of unpaid use.
ACTIVE_STATUSES = frozenset({"trialing", "active", "past_due"})

#: How many dossier exports one purchase grants.
CREDITS_PER_DOSSIER_PURCHASE = 1


class BillingError(RuntimeError):
    """Billing could not proceed. Carries a message meant for the operator."""


class BillingUnconfigured(BillingError):
    """No Stripe keys on this deployment. Not an error in development."""


class SignatureInvalid(BillingError):
    """The webhook payload did not come from Stripe, or the secret is wrong."""


@dataclass(frozen=True, slots=True)
class CheckoutRequest:
    org_id: str
    plan: PlanName
    customer_email: str | None
    stripe_customer_id: str | None
    success_url: str
    cancel_url: str


@dataclass(frozen=True, slots=True)
class SubscriptionState:
    """What a webhook says the subscription now is. Translated out of Stripe's shapes."""

    stripe_subscription_id: str
    stripe_customer_id: str
    stripe_price_id: str
    plan: PlanName
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool

    @property
    def grants_access(self) -> bool:
        return self.status in ACTIVE_STATUSES


@dataclass(frozen=True, slots=True)
class PurchaseState:
    """A completed one-off dossier purchase."""

    stripe_session_id: str
    stripe_customer_id: str | None
    stripe_payment_intent: str | None
    credits: int
    amount_cents: int | None
    currency: str | None


def _client(settings: Settings) -> Any:
    if not settings.stripe_secret_key:
        raise BillingUnconfigured(
            "STRIPE_SECRET_KEY is not set, so nothing can be bought on this deployment. "
            "See .env.example and the Third Party Setup Guide in docs/."
        )
    # A per-call client rather than the module-level global: the global would make the
    # key a process-wide fact and leak between tests.
    return stripe.StripeClient(settings.stripe_secret_key)


def plan_for_price(settings: Settings, price_id: str | None) -> PlanName | None:
    """Which plan a Stripe price id means, from configuration only.

    Never inferred from the price's nickname or amount: a product renamed in the Stripe
    dashboard must not silently change what a customer is entitled to.
    """
    if not price_id:
        return None
    for plan, configured in settings.stripe_prices.items():
        if configured == price_id:
            return plan  # type: ignore[return-value]
    return None


def available_plans(settings: Settings) -> dict[str, str]:
    """The plans this deployment can actually sell, as plan name → price id."""
    return {plan: price for plan, price in settings.stripe_prices.items() if plan in PLANS}


def create_checkout_session(settings: Settings, request: CheckoutRequest) -> str:
    """Start a Stripe Checkout session and return the URL to send the browser to.

    ``client_reference_id`` carries our org id through Stripe and back on the webhook, so
    the completed session is attributed to an organisation we chose rather than to one
    named in a request body.
    """
    # The key first, so a deployment with no Stripe at all says so rather than
    # complaining about a price id nobody was ever going to set.
    client = _client(settings)

    price = settings.stripe_prices.get(request.plan)
    if not price:
        raise BillingUnconfigured(
            f"No Stripe price is configured for the {request.plan} plan. "
            f"Set STRIPE_PRICE_{request.plan.upper()} and restart."
        )

    one_off = PLANS[request.plan].uses_dossier_credits
    params: dict[str, Any] = {
        "mode": "payment" if one_off else "subscription",
        "line_items": [{"price": price, "quantity": 1}],
        "success_url": request.success_url,
        "cancel_url": request.cancel_url,
        "client_reference_id": request.org_id,
        # Repeated here because `client_reference_id` is not copied onto the
        # subscription, and the subscription events are what arrive later.
        "metadata": {"org_id": request.org_id, "plan": request.plan},
    }
    if request.stripe_customer_id:
        params["customer"] = request.stripe_customer_id
    elif request.customer_email:
        params["customer_email"] = request.customer_email
    if not one_off:
        params["subscription_data"] = {"metadata": {"org_id": request.org_id, "plan": request.plan}}

    try:
        session = client.checkout.sessions.create(params=params)
    except stripe.StripeError as exc:
        raise BillingError(f"Stripe refused to open a checkout session: {exc}") from exc
    url = getattr(session, "url", None)
    if not url:
        raise BillingError("Stripe opened a checkout session without a URL.")
    return str(url)


def create_portal_session(settings: Settings, customer_id: str, return_url: str) -> str:
    """The Stripe-hosted page where a customer changes or cancels their own subscription.

    Hosted rather than rebuilt: card details and cancellation flows are Stripe's problem,
    and the less of that this product touches the better.
    """
    try:
        session = _client(settings).billing_portal.sessions.create(
            params={"customer": customer_id, "return_url": return_url}
        )
    except stripe.StripeError as exc:
        raise BillingError(f"Stripe refused to open the billing portal: {exc}") from exc
    url = getattr(session, "url", None)
    if not url:
        raise BillingError("Stripe opened a portal session without a URL.")
    return str(url)


def verify_event(settings: Settings, payload: bytes, signature: str | None) -> dict[str, Any]:
    """Verify the webhook signature and return the event as a plain dict.

    Nothing in the payload is read before this returns. A deployment without a webhook
    secret refuses rather than trusting the body: an unverified webhook is an open
    endpoint that grants plans.
    """
    if not settings.stripe_webhook_secret:
        raise BillingUnconfigured(
            "STRIPE_WEBHOOK_SECRET is not set, so webhooks cannot be verified and are "
            "refused. See the Third Party Setup Guide in docs/."
        )
    if not signature:
        raise SignatureInvalid("The request carried no Stripe-Signature header.")
    try:
        # The SDK ships this one untyped; the return is a StripeObject that behaves as
        # a mapping, which is all this function promises.
        event: Any = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload, signature, settings.stripe_webhook_secret
        )
    except ValueError as exc:
        raise SignatureInvalid("The webhook body is not valid JSON.") from exc
    except stripe.SignatureVerificationError as exc:
        raise SignatureInvalid("The webhook signature did not verify.") from exc
    return dict(event)


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, int | float) or value <= 0:
        return None
    return datetime.fromtimestamp(float(value), tz=UTC)


def _price_id(subscription: dict[str, Any]) -> str | None:
    items = (subscription.get("items") or {}).get("data") or []
    if not items:
        return None
    price = (items[0] or {}).get("price") or {}
    return str(price.get("id")) if price.get("id") else None


def _period_end(subscription: dict[str, Any]) -> datetime | None:
    """Stripe moved the period to the subscription item; read both shapes.

    Newer API versions report `current_period_end` per item rather than on the
    subscription. Reading only one shape would silently record `null` forever.
    """
    if (end := _timestamp(subscription.get("current_period_end"))) is not None:
        return end
    items = (subscription.get("items") or {}).get("data") or []
    for item in items:
        if (end := _timestamp((item or {}).get("current_period_end"))) is not None:
            return end
    return None


def subscription_state(settings: Settings, subscription: dict[str, Any]) -> SubscriptionState | None:
    """Translate a Stripe subscription object into what this product stores.

    Returns None when the price is not one this deployment sells — a subscription to
    some other product on the same Stripe account must not change anybody's plan.
    """
    price_id = _price_id(subscription)
    plan = plan_for_price(settings, price_id)
    if plan is None or price_id is None:
        return None
    customer = subscription.get("customer")
    customer_id = customer if isinstance(customer, str) else (customer or {}).get("id")
    if not customer_id or not subscription.get("id"):
        return None
    return SubscriptionState(
        stripe_subscription_id=str(subscription["id"]),
        stripe_customer_id=str(customer_id),
        stripe_price_id=price_id,
        plan=plan,
        status=str(subscription.get("status") or "incomplete"),
        current_period_end=_period_end(subscription),
        cancel_at_period_end=bool(subscription.get("cancel_at_period_end")),
    )


def purchase_state(settings: Settings, session: dict[str, Any]) -> PurchaseState | None:
    """Translate a completed one-off Checkout session into a credit grant.

    Returns None for a subscription checkout (handled by the subscription events), for an
    unpaid session, or for a session whose price this deployment does not sell.
    """
    if session.get("mode") != "payment":
        return None
    if session.get("payment_status") not in {"paid", "no_payment_required"}:
        return None
    if not session.get("id"):
        return None

    # The session's line items are not expanded on the webhook payload, so the plan is
    # read from the metadata we set when the session was created, and then confirmed
    # against configuration rather than trusted.
    metadata = session.get("metadata") or {}
    claimed = str(metadata.get("plan") or "")
    if claimed not in PLANS:
        return None
    if not PLANS[claimed].uses_dossier_credits:
        return None
    if "per_dossier" not in settings.stripe_prices:
        return None

    customer = session.get("customer")
    intent = session.get("payment_intent")
    return PurchaseState(
        stripe_session_id=str(session["id"]),
        stripe_customer_id=customer if isinstance(customer, str) else None,
        stripe_payment_intent=intent if isinstance(intent, str) else None,
        credits=CREDITS_PER_DOSSIER_PURCHASE,
        amount_cents=int(session["amount_total"]) if isinstance(session.get("amount_total"), int) else None,
        currency=str(session["currency"]) if session.get("currency") else None,
    )


def org_id_from(event_object: dict[str, Any]) -> str | None:
    """The organisation a Stripe object belongs to, from what we put there ourselves.

    ``client_reference_id`` on a Checkout session, ``metadata.org_id`` on either. Never
    from the customer email: two organisations can share one.
    """
    reference = event_object.get("client_reference_id")
    if isinstance(reference, str) and reference:
        return reference
    metadata = event_object.get("metadata") or {}
    org_id = metadata.get("org_id")
    return org_id if isinstance(org_id, str) and org_id else None
