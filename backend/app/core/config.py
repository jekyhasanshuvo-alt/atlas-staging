import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ATLAS_", extra="ignore", hide_input_in_errors=True
    )
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
    email_adapter: Literal["preview", "smtp", "staging_sink"] = "preview"
    staging_demo: bool = False
    staging_transport_key: SecretStr = SecretStr("")
    staging_mailbox_key: SecretStr = SecretStr("")
    staging_synthetic_emails: list[str] = Field(default_factory=list, max_length=8)
    staging_database_host: str = ""
    # These remain off until separately approved Neon role/account write scopes.
    staging_database_writes_enabled: bool = False
    staging_signup_enabled: bool = False
    pool_size: int = Field(default=5, ge=1, le=5)
    pool_max_overflow: int = Field(default=10, ge=0, le=10)
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
            or not (
                (self.email_adapter == "smtp" and self.smtp_host)
                or (self.staging_demo and self.email_adapter == "staging_sink")
            )
            or any(not origin.startswith("https://") for origin in self.cors_origins)
            or "*" in self.trusted_hosts
        ):
            raise ValueError(
                "Production requires Secure cookies, HTTPS origins, explicit hosts and secure mail"
            )
        if self.email_adapter == "staging_sink" and not self.staging_demo:
            raise ValueError("The non-delivering sink requires explicit staging mode")
        if self.staging_demo:
            parsed = make_url(self.database_url.get_secret_value())
            origin = urlsplit(self.frontend_url)
            keys = [
                self.staging_transport_key.get_secret_value(),
                self.staging_mailbox_key.get_secret_value(),
            ]
            if (
                self.environment != "production"
                or self.email_adapter != "staging_sink"
                or self.cors_origins != [self.frontend_url]
                or origin.scheme != "https"
                or not (origin.hostname or "").endswith(".onrender.com")
                or any(not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", key) for key in keys)
                or keys[0] == keys[1]
                or not self.staging_synthetic_emails
                or self.pool_size != 1
                or self.pool_max_overflow != 0
                or self.enable_demo_seed
                or self.experimental_foundation
                or self.experimental_journey
                or self.experimental_advisor
                or self.published_scholarships
                or self.cookie_name != "atlas_session"
                or len(self.trusted_hosts) != 1
                or not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.onrender\.com", self.trusted_hosts[0])
                or self.session_hours > 24
                or self.verification_minutes > 60
                or self.reset_minutes > 30
            ):
                raise ValueError(
                    "Staging requires isolated secure transport, sink, origins and bounded runtime"
                )
            if (
                parsed.database != "atlas_staging"
                or parsed.username != "atlas_staging_app"
                or not self.staging_database_host.startswith("ep-spring-rice-az3v9osg.")
                or not self.staging_database_host.endswith(".aws.neon.tech")
                or parsed.host != self.staging_database_host
                or parsed.port not in {None, 5432}
                or parsed.query.get("sslmode") != "verify-full"
                or not parsed.query.get("sslrootcert")
            ):
                raise ValueError(
                    "Staging requires the exact isolated Neon endpoint, app role and verified TLS"
                )
            if self.staging_signup_enabled and not self.staging_database_writes_enabled:
                raise ValueError("Staging signup requires separate database-write authorization")
        return self

    @field_validator("staging_synthetic_emails")
    @classmethod
    def reserved_demo_addresses(cls, values):
        if len(set(values)) != len(values) or any(
            not re.fullmatch(r"[a-z0-9][a-z0-9._+-]{0,63}@example\.(com|net|org)", value)
            for value in values
        ):
            raise ValueError(
                "Staging recipients must be exact, unique reserved example-domain addresses"
            )
        return values

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
