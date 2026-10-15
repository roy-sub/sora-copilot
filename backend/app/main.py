"""FastAPI application.

The product's invariant: a determination is computed by the clingo rules engine and by
nothing else. The LLM turns conversation into candidate facts the operator confirms, and
turns engine output into prose. ``tests/test_boundary.py`` enforces that structurally.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import router as v1_router
from app.config import get_settings
from app.problem import ProblemError, http_handler, problem_handler, validation_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("sora")

DESCRIPTION = """
Automates the EU drone Specific Operations Risk Assessment under EU 2019/947.

A symbolic rules engine (Answer Set Programming, clingo) computes the ground risk class,
the air risk class, SAIL, the required Operational Safety Objectives and the containment
requirement, each with a full justification trace and a pinned rulebase version.

SORA Copilot prepares and verifies your risk assessment. Your national aviation
authority grants the authorisation.
""".strip()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    missing = settings.validate_for_runtime()
    if missing:
        log.warning(
            "Running degraded in %s: missing %s. Auth and persistence are unavailable.",
            settings.env,
            ", ".join(missing),
        )
    log.info("SORA Copilot API up · env=%s · rulebase=%s", settings.env, settings.rulebase_version)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SORA Copilot API",
        description=DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.env != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(ProblemError, problem_handler)
    app.add_exception_handler(StarletteHTTPException, http_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)

    # /healthz sits at the root as well as under /api/v1, because the uptime monitor and
    # the Docker HEALTHCHECK both address it there.
    app.include_router(v1_router)
    app.include_router(v1_router, prefix="/api/v1")
    return app


app = create_app()
