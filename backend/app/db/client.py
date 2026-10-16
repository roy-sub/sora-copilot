"""Supabase client, built lazily with the service-role key.

The service-role key bypasses RLS by design, so **RLS is defence-in-depth here, not the
authorisation gate**. The gate is ``app.deps.get_org_context``, which derives org
membership from the verified JWT and never from the request body. RLS still covers every
table so that any future direct browser access is safe. See docs/ARCHITECTURE.md.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings
from app.problem import ProblemError


@lru_cache
def get_client() -> Client:
    s = get_settings()
    if not s.supabase_configured:
        raise ProblemError(
            code="database_unconfigured",
            title="The database is not configured",
            status_code=503,
            detail=(
                "SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and SUPABASE_JWT_SECRET are not set. "
                "See .env.example and docs/Deployment Guide.md."
            ),
        )
    return create_client(s.supabase_url, s.supabase_service_role_key)
