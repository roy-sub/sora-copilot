"""API v1 routers.

Mounted both at the root and under /api/v1 by app/main.py, so /healthz is reachable where
the uptime monitor and the Docker HEALTHCHECK look for it.
"""

from fastapi import APIRouter

from app.api.v1 import (
    determine,
    drones,
    geo,
    health,
    operations,
    orgs,
    public,
    rulebase,
)

router = APIRouter()
router.include_router(health.router)
router.include_router(orgs.router)
router.include_router(drones.router)
router.include_router(operations.router)
router.include_router(determine.router)
router.include_router(geo.router)
router.include_router(rulebase.router)
router.include_router(public.router)

__all__ = ["router"]
