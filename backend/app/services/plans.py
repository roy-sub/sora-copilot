"""What each plan allows. Pure data and pure functions — no Stripe, no database.

Separated from ``billing.py`` on purpose. Limits are read on every request that could
exceed one, including when Stripe is not configured at all, so this module must not
depend on a payment provider being present. ``billing.py`` maps a Stripe price to a plan
name; this module is the only place that says what a plan name *means*.

``None`` means unlimited. A limit of 0 means the feature is not on this plan, which is a
different message to the user than "you have used your three".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

PlanName = Literal["free", "per_dossier", "pro", "team", "consultancy"]

PLAN_NAMES: tuple[PlanName, ...] = ("free", "per_dossier", "pro", "team", "consultancy")


@dataclass(frozen=True, slots=True)
class Plan:
    name: PlanName
    label: str
    #: What the marketing page says. Kept here so the API can state it without the
    #: frontend hard-coding a price next to a limit it cannot see.
    price_label: str
    seats: int
    drones: int | None
    operations: int | None
    determinations_per_month: int | None
    #: Dossier exports per month. ``per_dossier`` has none of these and spends credits.
    dossiers_per_month: int | None
    #: A one-off purchase grants credits; each DOCX export spends one.
    uses_dossier_credits: bool
    counterfactuals: bool
    conversational_intake: bool
    evidence_files: int | None
    api_access: bool


PLANS: dict[PlanName, Plan] = {
    "free": Plan(
        name="free",
        label="Free",
        price_label="€0",
        seats=1,
        drones=2,
        operations=3,
        determinations_per_month=10,
        dossiers_per_month=0,
        uses_dossier_credits=False,
        counterfactuals=False,
        conversational_intake=False,
        evidence_files=0,
        api_access=False,
    ),
    "per_dossier": Plan(
        name="per_dossier",
        label="Per dossier",
        price_label="€149 per dossier",
        seats=1,
        drones=5,
        operations=10,
        determinations_per_month=50,
        dossiers_per_month=None,
        uses_dossier_credits=True,
        counterfactuals=True,
        conversational_intake=True,
        evidence_files=None,
        api_access=False,
    ),
    "pro": Plan(
        name="pro",
        label="Pro",
        price_label="€89 per month",
        seats=1,
        drones=None,
        operations=None,
        determinations_per_month=None,
        dossiers_per_month=None,
        uses_dossier_credits=False,
        counterfactuals=True,
        conversational_intake=True,
        evidence_files=None,
        api_access=False,
    ),
    "team": Plan(
        name="team",
        label="Team",
        price_label="€249 per month",
        seats=5,
        drones=None,
        operations=None,
        determinations_per_month=None,
        dossiers_per_month=None,
        uses_dossier_credits=False,
        counterfactuals=True,
        conversational_intake=True,
        evidence_files=None,
        api_access=True,
    ),
    "consultancy": Plan(
        name="consultancy",
        label="Consultancy",
        price_label="Contact us",
        seats=25,
        drones=None,
        operations=None,
        determinations_per_month=None,
        dossiers_per_month=None,
        uses_dossier_credits=False,
        counterfactuals=True,
        conversational_intake=True,
        evidence_files=None,
        api_access=True,
    ),
}

#: Every gated thing, and the sentence the operator reads when they hit it. The copy
#: lives next to the limit so the two cannot drift.
Feature = Literal[
    "drones",
    "operations",
    "determinations",
    "dossiers",
    "counterfactuals",
    "conversational_intake",
    "evidence",
    "seats",
    "api",
]


def plan_for(name: str | None) -> Plan:
    """The plan a stored name refers to, defaulting to free rather than failing.

    An unknown name means the database holds something this build does not know about —
    a rollback, or a plan added later. Falling back to free is the safe direction: it
    withholds features rather than granting them.
    """
    if name in PLANS:
        return PLANS[name]  # type: ignore[index]  # the `in` check is the narrowing
    return PLANS["free"]


@dataclass(frozen=True, slots=True)
class Denial:
    """Why a request was refused, in the operator's terms."""

    feature: Feature
    title: str
    detail: str
    limit: int | None
    used: int | None
    upgrade_to: PlanName | None

    @property
    def is_feature_gate(self) -> bool:
        """True when the plan never had the feature, as opposed to having used it up."""
        return self.limit == 0 or self.limit is None


def _cheapest_with(feature: Feature) -> PlanName | None:
    """The plan to name in the upsell: the first, in price order, that lifts the block.

    For a counted feature that means the first plan with *no* limit, not merely a higher
    one — telling someone who outgrew three operations to move to a plan with ten would
    be an upsell they resent a fortnight later. For a feature the plan simply lacks, it
    is the first plan that has it.
    """
    for name in PLAN_NAMES:
        if name == "free":
            continue
        plan = PLANS[name]
        allowed = {
            "drones": plan.drones is None,
            "operations": plan.operations is None,
            "determinations": plan.determinations_per_month is None,
            "dossiers": plan.uses_dossier_credits or plan.dossiers_per_month is None,
            "counterfactuals": plan.counterfactuals,
            "conversational_intake": plan.conversational_intake,
            "evidence": plan.evidence_files is None,
            "seats": plan.seats > 1,
            "api": plan.api_access,
        }[feature]
        if allowed:
            return name
    return None


def _count_limit(feature: Feature, plan: Plan) -> int | None:
    return {
        "drones": plan.drones,
        "operations": plan.operations,
        "determinations": plan.determinations_per_month,
        "dossiers": plan.dossiers_per_month,
        "evidence": plan.evidence_files,
        "seats": plan.seats,
    }.get(feature)


#: How each counted thing is named in the sentence the operator reads.
_FEATURE_NOUN: dict[Feature, str] = {
    "drones": "aircraft in the fleet",
    "operations": "operations",
    "determinations": "determinations this month",
    "dossiers": "dossier exports this month",
    "evidence": "evidence files",
    "seats": "seats",
}


def check_count(feature: Feature, plan: Plan, used: int) -> Denial | None:
    """Refuse when adding one more would exceed the plan's count for `feature`."""
    limit = _count_limit(feature, plan)
    if limit is None:
        return None
    plural = _FEATURE_NOUN[feature]
    upgrade = _cheapest_with(feature)
    if limit == 0:
        return Denial(
            feature=feature,
            title=f"The {plan.label} plan has no {plural}",
            detail=(
                f"{plan.label} does not include {plural}. "
                + (f"{PLANS[upgrade].label} does." if upgrade else "")
            ).strip(),
            limit=0,
            used=used,
            upgrade_to=upgrade,
        )
    if used >= limit:
        return Denial(
            feature=feature,
            title=f"You have reached the {plan.label} limit of {limit} {plural}",
            detail=(
                f"{plan.label} includes {limit} {plural}; you have {used}. "
                + (f"{PLANS[upgrade].label} removes the limit." if upgrade else "")
            ).strip(),
            limit=limit,
            used=used,
            upgrade_to=upgrade,
        )
    return None


def check_feature(feature: Feature, plan: Plan) -> Denial | None:
    """Refuse a feature the plan does not include at all."""
    allowed = {
        "counterfactuals": plan.counterfactuals,
        "conversational_intake": plan.conversational_intake,
        "api": plan.api_access,
    }.get(feature)
    if allowed is None or allowed:
        return None
    titles: dict[str, tuple[str, str]] = {
        "counterfactuals": (
            "The counterfactual advisor is not on this plan",
            "It searches the rulebase for the smallest change that would lower your SAIL.",
        ),
        "conversational_intake": (
            "Conversational intake is not on this plan",
            "Describe the operation in prose and confirm the facts it proposes. "
            "The wizard's form collects the same facts on every plan.",
        ),
        "api": ("API access is not on this plan", "Programmatic access is available on Team."),
    }
    title, detail = titles[feature]
    upgrade = _cheapest_with(feature)
    if upgrade:
        detail = f"{detail} Available on {PLANS[upgrade].label}."
    return Denial(feature=feature, title=title, detail=detail, limit=0, used=None, upgrade_to=upgrade)


def check_dossier(plan: Plan, *, used_this_month: int, credits: int) -> Denial | None:
    """Dossiers are the one thing that can be bought one at a time.

    A credit is checked before the monthly allowance, so a one-off purchase works on any
    plan — including a subscriber who has exhausted a limited allowance.
    """
    if credits > 0:
        return None
    if plan.uses_dossier_credits:
        return Denial(
            feature="dossiers",
            title="No dossier credits left",
            detail=(
                "The per-dossier plan spends one credit per export. Buy another, or move "
                "to Pro for unlimited exports."
            ),
            limit=0,
            used=used_this_month,
            upgrade_to="pro",
        )
    if plan.dossiers_per_month == 0:
        return Denial(
            feature="dossiers",
            title=f"The {plan.label} plan does not export dossiers",
            detail=(
                "The determination, its trace and the OSO matrix are yours to read on "
                "every plan. The authority-ready DOCX export is not: buy a single dossier, "
                "or move to Pro for unlimited exports."
            ),
            limit=0,
            used=used_this_month,
            upgrade_to="per_dossier",
        )
    return check_count("dossiers", plan, used_this_month)


def month_start(now: datetime | None = None) -> datetime:
    """The boundary every monthly allowance is measured from. UTC, first of the month."""
    moment = now or datetime.now(UTC)
    return moment.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
