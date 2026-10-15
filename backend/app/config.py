"""Settings. Every key here appears in the repo's .env.example (build spec §13).

Development runs degraded with keys missing, so the skeleton is runnable before a
Supabase project exists. Production refuses to start without them — a compliance product
should not come up half-configured and look healthy.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)

Env = Literal["development", "test", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    env: Env = "development"
    git_sha: str = Field(default="unknown", description="Injected at deploy time for /healthz.")

    # ---------------------------------------------------------------- Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # ---------------------------------------------------------------- Anthropic
    # The spec pinned claude-sonnet-4-6, which is not a current model id; PLAN.md §0
    # records the default moving to the current Sonnet. Env-driven, so this is only a default.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    llm_monthly_call_cap: int = Field(default=500, ge=0)

    # ---------------------------------------------------------------- Stripe (phase 8)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # ---------------------------------------------------------------- Rulebase
    rulebase_version: str = "2.5.0-rc1"

    # ---------------------------------------------------------------- HTTP
    cors_origins: str = "http://localhost:3000"

    @field_validator("cors_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key and self.supabase_jwt_secret)

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key)

    def validate_for_runtime(self) -> list[str]:
        """Return the missing-key warnings, or raise in production where they are fatal."""
        missing: list[str] = []
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_service_role_key:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if not self.supabase_jwt_secret:
            missing.append("SUPABASE_JWT_SECRET")

        if not missing:
            return []
        if self.env == "production":
            raise RuntimeError(
                "Refusing to start in production without: " + ", ".join(missing)
            )
        return missing


@lru_cache
def get_settings() -> Settings:
    return Settings()
