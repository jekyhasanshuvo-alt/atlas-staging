from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ATLAS_", extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = SecretStr("postgresql+psycopg://atlas@127.0.0.1:5432/atlas")
    test_database_url: SecretStr | None = None
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    enable_demo_seed: bool = False
    # Synthetic disposable testing only, never an operational schema/privacy approval.
    experimental_foundation: bool = False
    experimental_journey: bool = False
    experimental_advisor: bool = False
    review_operator: str = ""
    frontend_url: str = "http://127.0.0.1:3000"
    cookie_name: str = "atlas_session"
    cookie_secure: bool = False
    session_hours: int = 168
    verification_minutes: int = Field(default=1440, ge=1, le=10080)
    reset_minutes: int = Field(default=30, ge=1, le=1440)
    reset_revokes_sessions: bool = True
    email_adapter: Literal["preview", "smtp"] = "preview"
    mail_directory: str = ".local/mail"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "atlas@localhost"
    rate_limit: int = 10
    rate_window_seconds: int = 900
    trusted_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    # Empty by default. Setting this is a separate operational publication action.
    published_scholarships: dict[str, str] = Field(default_factory=dict, max_length=200)

    @field_validator("published_scholarships")
    @classmethod
    def publication_ids(cls, values):
        if any(
            not 1 <= len(v) <= 36 or not v.isascii() or not all(c.isalnum() or c in "_-" for c in v)
            for v in values
        ) or any(
            len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
            for digest in values.values()
        ):
            raise ValueError("Publication requires bounded IDs and exact SHA-256 approval digests")
        return values

    @model_validator(mode="after")
    def secure_production(self):
        if (
            not 1 <= self.session_hours <= 720
            or not 1 <= self.rate_limit <= 1000
            or self.rate_window_seconds < 1
        ):
            raise ValueError("Invalid session or throttling configuration")
        if self.frontend_url.rstrip("/") not in self.cors_origins:
            raise ValueError("Frontend URL must be an allowed origin")
        if self.environment == "production" and (
            not self.cookie_secure
            or self.email_adapter != "smtp"
            or not self.smtp_host
            or any(not origin.startswith("https://") for origin in self.cors_origins)
            or "*" in self.trusted_hosts
        ):
            raise ValueError(
                "Production requires Secure cookies, HTTPS origins, explicit hosts and SMTP"
            )
        return self

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: SecretStr) -> SecretStr:
        if make_url(value.get_secret_value()).drivername != "postgresql+psycopg":
            raise ValueError("Use PostgreSQL with the psycopg driver")
        return value

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, values: list[str]) -> list[str]:
        if not values or any(
            (
                lambda parsed: (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.path
                    or parsed.query
                    or parsed.fragment
                )
            )(urlsplit(v))
            for v in values
        ):
            raise ValueError("CORS requires explicit HTTP(S) origins")
        return values
