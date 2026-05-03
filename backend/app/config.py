"""Settings loaded from environment / .env via pydantic-settings.

Settings is a singleton — call :func:`get_settings` everywhere. The `lru_cache`
makes it cheap to inject as a FastAPI dependency.

Environment variables are documented in `.env.example` at the repo root.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


# Banned watsonx model identifiers — must match docs/AGENTS.md.
# Any attempt to instantiate the client with one of these raises at construction.
BANNED_WATSONX_MODELS: frozenset[str] = frozenset(
    {
        "llama-3-405b-instruct",
        "mistral-medium-2505",
        "mistral-small-3-1-24b-instruct-2503",
    }
)


class Settings(BaseSettings):
    """Backend runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App identity ----------------------------------------------------
    app_name: str = "helios-backend"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")  # development | staging | production
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # json | console

    # --- HTTP server -----------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: str = Field(
        default="http://localhost:3000,https://golden007-prog.github.io"
    )

    # --- Auth ------------------------------------------------------------
    # JWT_SECRET is per-developer; the seeded demo user passwords are fixed.
    jwt_secret: str = Field(default="dev-secret-change-me", min_length=8)
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 24 * 3600
    demo_user_password: str = "helios2026"

    # --- Cloudant --------------------------------------------------------
    cloudant_url: HttpUrl | None = None
    cloudant_apikey: str | None = None
    cloudant_db_prefix: str = "helios_"
    cloudant_timeout_seconds: float = 5.0
    cloudant_max_retries: int = 3

    # --- watsonx.ai ------------------------------------------------------
    watsonx_url: HttpUrl = Field(default=HttpUrl("https://us-south.ml.cloud.ibm.com"))
    watsonx_project_id: str | None = None
    watsonx_apikey: str | None = None
    watsonx_default_model: str = "ibm/granite-code-8b-instruct"
    watsonx_chat_model: str = "ibm/granite-3-8b-instruct"
    watsonx_timeout_seconds: float = 30.0
    watsonx_max_retries: int = 2

    # --- IBM Cloud (used by ibm-cloud MCP) -------------------------------
    ibm_cloud_api_key: str | None = None
    ibm_cloud_region: str = "us-south"

    # --- Demo / fixtures -------------------------------------------------
    shop: str = "meridianbank"

    # --- Feature gates ---------------------------------------------------
    # Set to False in tests / CI where Cloudant + watsonx aren't reachable.
    enable_cloudant: bool = True
    enable_watsonx: bool = True

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, v: str) -> str:
        return ",".join(part.strip() for part in v.split(",") if part.strip())

    @field_validator("cloudant_url", "cloudant_apikey", "watsonx_apikey", "watsonx_project_id", mode="before")
    @classmethod
    def _empty_to_none(cls, v: object) -> object:
        # `.env.example` ships empty values; treat "" as not-set so the
        # backend boots in degraded mode rather than failing URL validation.
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o for o in self.cors_origins.split(",") if o]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def assert_model_allowed(self, model_id: str) -> None:
        """Raise if the model id is in the banned set (see docs/AGENTS.md).

        Called by the watsonx client at every inference and also at startup
        when a default model is configured. Banning is checked by suffix
        match on the model id (the watsonx provider prefix is optional).
        """
        bare = model_id.split("/")[-1].lower()
        if bare in BANNED_WATSONX_MODELS:
            raise ValueError(
                f"watsonx model '{model_id}' is on the Helios banned list "
                f"(see docs/AGENTS.md § Hard rules)"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached :class:`Settings` instance."""
    return Settings()


def reset_settings_cache() -> None:
    """Tests use this to force a re-read after monkey-patching env vars."""
    get_settings.cache_clear()
