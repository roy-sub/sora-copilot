"""API v1 routers.

Mounted both at the root and under /api/v1 by app/main.py, so /healthz is reachable where
the uptime monitor and the Docker HEALTHCHECK look for it.
"""

from fastapi import APIRouter

from app.api.v1 import (
    billing,
    determine,
    dossier,
    drones,
    geo,
    health,
    intake_chat,
    national,
    operations,
    orgs,
    public,
    rulebase,
)

router = APIRouter()
router.include_router(health.router)
router.include_router(orgs.router)
router.include_router(billing.router)
router.include_router(drones.router)
router.include_router(operations.router)
router.include_router(determine.router)
router.include_router(dossier.router)
router.include_router(geo.router)
router.include_router(intake_chat.router)
router.include_router(national.router)
router.include_router(rulebase.router)
router.include_router(public.router)

__all__ = ["router"]
