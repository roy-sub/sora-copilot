"""Storage. One interface, two implementations — see app/db/repo.py."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.db.repo import MemoryRepo, NotFound, Repo, Row

__all__ = ["MemoryRepo", "NotFound", "Repo", "Row", "get_repo", "reset_repo"]


@lru_cache
def get_repo() -> Repo:
    """Supabase when it is configured; the in-memory store otherwise.

    Falling back rather than failing is deliberate: the whole product — API, wizard,
    engine, dossier — runs locally with no account and no keys, which is what makes it
    reviewable before anything is provisioned. ``/healthz`` and the UI both say the
    storage is not durable, so nobody can mistake it for a database.
    """
    settings = get_settings()
    if settings.supabase_configured:
        from app.db.supabase_repo import SupabaseRepo

        return SupabaseRepo()
    return MemoryRepo()


def reset_repo() -> None:
    """Drop the cached repository. Used by the tests and after a settings change."""
    get_repo.cache_clear()
