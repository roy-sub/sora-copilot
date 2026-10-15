"""Health checks.

``/healthz`` is deliberately dependency-free: it must answer while Supabase is paused,
because an external uptime monitor pings it to keep the Render free instance awake
(build spec §14). Database reachability lives in ``/healthz/deep``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    env: str
    rulebase_version: str
    git_sha: str
    supabase_configured: bool
    anthropic_configured: bool


class DeepHealth(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unreachable", "unconfigured"]
    detail: str | None = None


@router.get("/healthz", response_model=Health, summary="Liveness — no dependencies")
def healthz(settings: Annotated[Settings, Depends(get_settings)]) -> Health:
    return Health(
        env=settings.env,
        rulebase_version=settings.rulebase_version,
        git_sha=settings.git_sha,
        supabase_configured=settings.supabase_configured,
        anthropic_configured=settings.anthropic_configured,
    )


@router.get("/healthz/deep", response_model=DeepHealth, summary="Readiness — checks the database")
def healthz_deep(settings: Annotated[Settings, Depends(get_settings)]) -> DeepHealth:
    if not settings.supabase_configured:
        return DeepHealth(
            status="degraded",
            database="unconfigured",
            detail="Supabase keys are not set. See .env.example.",
        )
    try:
        from app.db.client import get_client

        get_client().table("rulebase_versions").select("version").limit(1).execute()
    except Exception as exc:  # any failure at all reads as "unreachable" to a caller
        return DeepHealth(status="degraded", database="unreachable", detail=str(exc)[:200])
    return DeepHealth(status="ok", database="ok")
