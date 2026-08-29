"""Typed settings from the environment, including the derived database URL (DEP-051).

Every variable this reads is documented with no value in `.env.example`
(DEP-018, DEP-047). Production sets them with `fly secrets`, never in
`fly.toml` (DEP-023).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Everything the application reads from its environment.

    `JWT_SECRET` has **no default, deliberately**. A default secret in code is
    worse than no auth at all, because it looks like auth: startup fails loudly
    instead (AUTH-014, AUTH-017). The 32-character floor is enforced here rather
    than checked somewhere later, so a short secret cannot reach a running
    process.
    """

    model_config = SettingsConfigDict(extra="ignore")

    data_dir: Path = Path("/data")
    jwt_secret: str = Field(min_length=32)
    environment: str = "production"
    otel_exporter_otlp_endpoint: str = ""
    ai_classification_enabled: bool = False
    anthropic_api_key: str = ""

    @property
    def database_url(self) -> str:
        """Build the database URL from `data_dir`.

        **Derived, never read from the environment.** Setting both would give
        one path two sources: change `DATA_DIR` and the database quietly stays
        where it was (DEP-051, CQ-081).
        """
        return f"sqlite+aiosqlite:///{self.data_dir}/app.db"

    @property
    def blob_dir(self) -> Path:
        """Where uploaded blobs live, beside the database on the same volume.

        They are separate stores and must not be conflated (ARC-010), but they
        share the volume so that neither survives a restart without the other
        (DEP-003, DEP-004).
        """
        return self.data_dir / "blobs"

    @property
    def is_development(self) -> bool:
        """Whether the session cookie may be sent without TLS (AUTH-018)."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Read the environment once and reuse it.

    Cached because `Settings()` reads the environment on construction and a
    dependency runs per request; without this, every request would re-parse and
    re-validate the same values.
    """
    return Settings()  # type: ignore[call-arg]  # pydantic-settings fills these from the environment
