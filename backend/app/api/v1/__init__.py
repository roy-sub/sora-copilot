"""API v1 routers.

Routers land as their phase does. Phase 1 ships health only; nothing is stubbed to
return a plausible value, because a stub that answers is worse than a 404.
"""

from fastapi import APIRouter

from app.api.v1 import health

router = APIRouter()
router.include_router(health.router)

__all__ = ["router"]
