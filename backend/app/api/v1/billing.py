"""Checkout, the billing portal, and the Stripe webhook.

The webhook is the only unauthenticated write endpoint in the product. What makes that
acceptable:

* the payload is verified against the endpoint secret before any field is read;
* the event id is claimed in the database before the handler runs, so a redelivery is a
  no-op;
* the organisation is taken from ``client_reference_id``/``metadata.org_id`` — values
  this product set when it opened the session — never from an email or a name;
* a plan is derived from a configured price id, so renaming a product in the Stripe
  dashboard cannot change anyone's entitlements.

Everything the request path reads lives on ``orgs.plan`` and ``orgs.dossier_credits``.
The ``subscriptions`` table is the record of *why* the plan is what it is, and nothing
reads it to decide access.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin, urlparse

from fastapi import APIRouter, Request, status

from app.api.v1.deps_api import RepoDep, SettingsDep
from app.api.v1.gate import GateDep
from app.api.v1.schemas import (
    BillingStateOut,
    CheckoutIn,
    CheckoutOut,
    PlanLimitsOut,
    PlanOut,
    PortalOut,
    WebhookOut,
)
from app.config import Settings
from app.db.repo import NotFound, Repo, Row
from app.deps import OrgContextDep
from app.problem import ProblemError
from app.services import billing, plans

log = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


def _plan_out(plan: plans.Plan, purchasable: bool) -> PlanOut:
    return PlanOut(
        name=plan.name,
        label=plan.label,
        price_label=plan.price_label,
        purchasable=purchasable,
        limits=PlanLimitsOut(
            seats=plan.seats,
            drones=plan.drones,
            operations=plan.operations,
            determinations_per_month=plan.determinations_per_month,
            dossiers_per_month=plan.dossiers_per_month,
            evidence_files=plan.evidence_files,
            counterfactuals=plan.counterfactuals,
            conversational_intake=plan.conversational_intake,
            api_access=plan.api_access,
            uses_dossier_credits=plan.uses_dossier_credits,
        ),
    )


def _unconfigured(exc: billing.BillingUnconfigured) -> ProblemError:
    return ProblemError(
        code="billing_unconfigured",
        title="Payments are not set up on this deployment",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    )


# ------------------------------------------------------------------ reading the state


@router.get("", response_model=BillingStateOut, summary="The plan, its limits, and usage")
def state(ctx: OrgContextDep, repo: RepoDep, gate: GateDep, settings: SettingsDep) -> BillingStateOut:
    org = repo.get_org(ctx.org_id)
    sellable = billing.available_plans(settings)
    subscriptions = repo.list_subscriptions(ctx.org_id)
    current = next(
        (s for s in subscriptions if str(s.get("status")) in billing.ACTIVE_STATUSES),
        subscriptions[0] if subscriptions else None,
    )
    return BillingStateOut(
        plan=_plan_out(gate.plan, gate.plan.name in sellable),
        dossier_credits=gate.credits,
        usage=gate.usage(),
        status=str(current["status"]) if current else None,
        current_period_end=current.get("current_period_end") if current else None,
        cancel_at_period_end=bool(current.get("cancel_at_period_end")) if current else False,
        billing_configured=settings.stripe_configured,
        can_manage=ctx.can_admin,
        plans=[
            _plan_out(plan, name in sellable)
            for name, plan in plans.PLANS.items()
            if name != "consultancy"
        ],
        portal_available=bool(settings.stripe_configured and org.get("stripe_customer_id")),
    )


# ------------------------------------------------------------------ buying


def _return_url(settings: Settings, path: str) -> str:
    """Resolve a caller-supplied path against the configured frontend origin.

    Only the path is taken from the request. An open redirect in a checkout flow is how
    a payment confirmation ends up on somebody else's page, so the host is never the
    caller's to choose.
    """
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        raise ProblemError(
            code="validation_failed",
            title="The return path must be a path, not a URL",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Pass a path such as /app/settings/. The origin is set by the server.",
        )
    return urljoin(settings.stripe_return_url, path if path.startswith("/") else f"/{path}")


@router.post("/checkout", response_model=CheckoutOut, summary="Open a Stripe Checkout session")
def checkout(
    body: CheckoutIn,
    ctx: OrgContextDep,
    repo: RepoDep,
    settings: SettingsDep,
) -> CheckoutOut:
    if not ctx.can_admin:
        raise ProblemError(
            code="forbidden",
            title="Only an owner or admin can start a purchase",
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ask an owner of this organisation to make the change.",
        )
    org = repo.get_org(ctx.org_id)
    request = billing.CheckoutRequest(
        org_id=str(ctx.org_id),
        plan=body.plan,
        customer_email=ctx.user.email,
        stripe_customer_id=str(org["stripe_customer_id"]) if org.get("stripe_customer_id") else None,
        success_url=_return_url(settings, body.success_path),
        cancel_url=_return_url(settings, body.cancel_path),
    )
    try:
        url = billing.create_checkout_session(settings, request)
    except billing.BillingUnconfigured as exc:
        raise _unconfigured(exc) from exc
    except billing.BillingError as exc:
        raise ProblemError(
            code="checkout_failed",
            title="The checkout session could not be opened",
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    mode = "payment" if plans.PLANS[body.plan].uses_dossier_credits else "subscription"
    return CheckoutOut(url=url, plan=body.plan, mode=mode)


@router.post("/portal", response_model=PortalOut, summary="Open the Stripe billing portal")
def portal(ctx: OrgContextDep, repo: RepoDep, settings: SettingsDep) -> PortalOut:
    if not ctx.can_admin:
        raise ProblemError(
            code="forbidden",
            title="Only an owner or admin can manage billing",
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ask an owner of this organisation to make the change.",
        )
    org = repo.get_org(ctx.org_id)
    customer_id = org.get("stripe_customer_id")
    if not customer_id:
        raise ProblemError(
            code="no_customer",
            title="There is nothing to manage yet",
            status_code=status.HTTP_409_CONFLICT,
            detail="This organisation has never been through checkout, so Stripe has no record of it.",
        )
    try:
        url = billing.create_portal_session(settings, str(customer_id), settings.stripe_return_url)
    except billing.BillingUnconfigured as exc:
        raise _unconfigured(exc) from exc
    except billing.BillingError as exc:
        raise ProblemError(
            code="portal_failed",
            title="The billing portal could not be opened",
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return PortalOut(url=url)


# ------------------------------------------------------------------ the webhook


def _resolve_org(repo: Repo, event_object: dict[str, Any], customer_id: str | None) -> Row | None:
    """Which organisation an event is about, by id first and customer second."""
    org_id = billing.org_id_from(event_object)
    if org_id:
        try:
            return repo.get_org(org_id)
        except (NotFound, ValueError):
            log.warning("stripe event names org %s, which does not exist", org_id)
    if customer_id:
        return repo.org_for_stripe_customer(customer_id)
    return None


def _apply_subscription(repo: Repo, settings: Settings, obj: dict[str, Any]) -> str:
    sub = billing.subscription_state(settings, obj)
    if sub is None:
        # A subscription to some other product on the same Stripe account.
        return "ignored"
    org = _resolve_org(repo, obj, sub.stripe_customer_id)
    if org is None:
        log.warning("stripe subscription %s matches no organisation", sub.stripe_subscription_id)
        return "ignored"

    repo.upsert_subscription(
        org["id"],
        {
            "stripe_subscription_id": sub.stripe_subscription_id,
            "stripe_customer_id": sub.stripe_customer_id,
            "stripe_price_id": sub.stripe_price_id,
            "plan": sub.plan,
            "status": sub.status,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
        },
    )
    # A lapsed subscription returns the organisation to free rather than deleting
    # anything: the determinations and dossiers already produced stay readable, which is
    # what a compliance record has to do.
    patch: Row = {
        "plan": sub.plan if sub.grants_access else "free",
        "stripe_customer_id": sub.stripe_customer_id,
        "stripe_subscription_id": sub.stripe_subscription_id,
        "plan_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
    }
    repo.update_org(org["id"], patch)
    return "applied"


def _apply_checkout(repo: Repo, settings: Settings, obj: dict[str, Any]) -> str:
    """A completed Checkout session. Only the one-off dossier purchase is settled here.

    A subscription checkout also emits ``customer.subscription.created``, which is where
    the plan is set; doing it in both places would be two sources of truth.
    """
    customer = obj.get("customer")
    org = _resolve_org(repo, obj, customer if isinstance(customer, str) else None)
    if org is None:
        log.warning("stripe checkout session %s matches no organisation", obj.get("id"))
        return "ignored"

    # Remember the customer id whatever the mode, so the portal works afterwards.
    if isinstance(customer, str) and customer and not org.get("stripe_customer_id"):
        repo.update_org(org["id"], {"stripe_customer_id": customer})

    purchase = billing.purchase_state(settings, obj)
    if purchase is None:
        return "ignored"
    repo.record_purchase(
        org["id"],
        {
            "stripe_session_id": purchase.stripe_session_id,
            "stripe_payment_intent": purchase.stripe_payment_intent,
            "credits": purchase.credits,
            "amount_cents": purchase.amount_cents,
            "currency": purchase.currency,
        },
    )
    repo.grant_dossier_credits(org["id"], purchase.credits)
    # The one-off buyer sits on `per_dossier` so the counterfactual advisor and the prose
    # panel are available while they prepare the dossier they paid for. A subscriber is
    # left alone: a credit purchase must never demote a Pro customer.
    if plans.plan_for(org.get("plan")).name == "free":
        repo.update_org(org["id"], {"plan": "per_dossier"})
    return "applied"


def _apply_payment_failed(repo: Repo, obj: dict[str, Any]) -> str:
    """A failed invoice is recorded but does not cut access.

    Stripe moves the subscription to ``past_due`` and then to ``canceled`` or ``unpaid``
    on its own schedule, and those events are what change the plan. Downgrading on the
    first failed card would strand an operator mid-application over a bank decline.
    """
    customer = obj.get("customer")
    org = _resolve_org(repo, obj, customer if isinstance(customer, str) else None)
    if org is None:
        return "ignored"
    log.warning("stripe invoice payment failed for org %s", org["id"])
    return "applied"


@router.post(
    "/webhook",
    response_model=WebhookOut,
    summary="Stripe events — signature-verified, idempotent, unauthenticated",
)
async def webhook(request: Request, repo: RepoDep, settings: SettingsDep) -> WebhookOut:
    payload = await request.body()
    try:
        event = billing.verify_event(settings, payload, request.headers.get("stripe-signature"))
    except billing.BillingUnconfigured as exc:
        raise _unconfigured(exc) from exc
    except billing.SignatureInvalid as exc:
        # 400, not 401: there is no identity to challenge. Stripe treats both as a
        # failure and retries, which is what should happen if the secret is wrong.
        raise ProblemError(
            code="signature_invalid",
            title="The webhook signature did not verify",
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    if not event_id:
        raise ProblemError(
            code="validation_failed",
            title="The event carries no id",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An event without an id cannot be made idempotent, so it is refused.",
        )

    obj = dict(((event.get("data") or {}).get("object")) or {})
    customer = obj.get("customer")
    org = _resolve_org(repo, obj, customer if isinstance(customer, str) else None)

    # Claimed before the handler runs. A handler that fails half-way must not be retried
    # blindly against state it has already changed.
    first_time = repo.remember_stripe_event(
        event_id,
        {
            "type": event_type,
            "org_id": org["id"] if org else None,
            "event_created": event.get("created"),
            "payload": {"id": event_id, "type": event_type},
        },
    )
    if not first_time:
        return WebhookOut(received=True, outcome="duplicate")

    if event_type not in billing.HANDLED:
        return WebhookOut(received=True, outcome="ignored")

    if event_type == "checkout.session.completed":
        outcome = _apply_checkout(repo, settings, obj)
    elif event_type == "invoice.payment_failed":
        outcome = _apply_payment_failed(repo, obj)
    else:
        outcome = _apply_subscription(repo, settings, obj)

    return WebhookOut(received=True, outcome="applied" if outcome == "applied" else "ignored")
