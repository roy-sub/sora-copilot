"""Plan gating: the one place a request is refused for commercial rather than
regulatory reasons.

Kept separate from the endpoints so the refusal is always shaped the same way — a 402
with the feature, the limit, what has been used and which plan lifts it — and so a new
gated endpoint cannot invent its own message.

402 rather than 403: the request was understood and the caller is who they say they are.
What is missing is payment. The frontend branches on ``code == "plan_limit"`` and renders
the upgrade panel from the fields rather than parsing the prose.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, status

from app.api.v1.deps_api import RepoDep
from app.db.repo import Repo
from app.deps import OrgContext, OrgContextDep
from app.problem import ProblemError
from app.services import plans
from app.services.plans import Denial, Feature, Plan


def _refuse(denial: Denial, plan: Plan) -> ProblemError:
    return ProblemError(
        code="plan_limit",
        title=denial.title,
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=denial.detail,
        feature=denial.feature,
        plan=plan.name,
        limit=denial.limit,
        used=denial.used,
        upgrade_to=denial.upgrade_to,
    )


@dataclass(frozen=True, slots=True)
class Gate:
    """What this organisation may do, and the counts behind that answer.

    Usage is read lazily, one query per feature actually checked, so an endpoint that
    gates nothing costs nothing.
    """

    repo: Repo
    org_id: str
    plan: Plan
    credits: int

    # -------------------------------------------------------------- counts

    def _used(self, feature: Feature) -> int:
        counters: dict[str, Callable[[str], int]] = {
            "drones": self.repo.count_drones,
            "operations": self.repo.count_operations,
            "evidence": self.repo.count_evidence,
            "determinations": self.repo.count_determinations_this_month,
            "dossiers": self.repo.count_dossiers_this_month,
            "seats": lambda org_id: len(self.repo.members(org_id)),
        }
        return counters[feature](self.org_id)

    def require_count(self, feature: Feature) -> None:
        """Refuse when one more of `feature` would exceed the plan."""
        denial = plans.check_count(feature, self.plan, self._used(feature))
        if denial is not None:
            raise _refuse(denial, self.plan)

    def require_feature(self, feature: Feature) -> None:
        """Refuse a feature this plan does not include at all."""
        denial = plans.check_feature(feature, self.plan)
        if denial is not None:
            raise _refuse(denial, self.plan)

    def require_dossier(self) -> bool:
        """Refuse an export, or report whether a credit must be spent for it.

        Returns True when the caller must call ``spend_dossier_credit`` once the export
        has succeeded. Checking and spending are separate on purpose: a credit is not
        burned by a generation that then fails.
        """
        denial = plans.check_dossier(
            self.plan,
            used_this_month=self._used("dossiers"),
            credits=self.credits,
        )
        if denial is not None:
            raise _refuse(denial, self.plan)
        return self.credits > 0

    # -------------------------------------------------------------- reporting

    def usage(self) -> dict[str, int]:
        """Every counted dimension, for the settings screen. One query each."""
        return {
            "drones": self._used("drones"),
            "operations": self._used("operations"),
            "evidence": self._used("evidence"),
            "determinations_this_month": self._used("determinations"),
            "dossiers_this_month": self._used("dossiers"),
            "seats": self._used("seats"),
        }


def get_gate(ctx: OrgContextDep, repo: RepoDep) -> Gate:
    org = repo.get_org(ctx.org_id)
    return Gate(
        repo=repo,
        org_id=str(ctx.org_id),
        plan=plans.plan_for(org.get("plan")),
        credits=int(org.get("dossier_credits") or 0),
    )


GateDep = Annotated[Gate, Depends(get_gate)]


def require_admin(ctx: OrgContext) -> None:
    """Billing changes are an owner's decision, not a member's."""
    if not ctx.can_admin:
        raise ProblemError(
            code="forbidden",
            title="Only an owner or admin can change billing",
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ask an owner of this organisation to make the change.",
        )
