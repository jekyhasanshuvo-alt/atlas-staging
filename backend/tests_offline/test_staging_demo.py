"""Offline ASGI/security checks. No PostgreSQL fixture, socket or database writes."""

import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "backend"))
for name in list(os.environ):
    if name.startswith("ATLAS_"):
        os.environ.pop(name)
os.environ["ATLAS_DATABASE_URL"] = "postgresql+psycopg://127.0.0.1:1/atlas_offline_only"
from app.core.config import Settings

Settings.model_config["env_file"] = None
import psycopg
import pytest

connection_attempts = []


def forbidden(*args, **kwargs):
    connection_attempts.append(True)
    raise AssertionError("Database/network use forbidden")


psycopg.connect = forbidden
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1 import auth
from app.db.session import get_session
from app.main import create_app
from app.models.student import AuthSession, User
from app.services.email import deliver
from app.services.security import digest, now
from app.services.staging_mail import StagingMailbox

KEY = "T" * 43
MAIL_KEY = "M" * 43
FRONTEND = "https://demo-web.onrender.com"
BACKEND = "https://demo-api.onrender.com"
EMAIL_A = "atlas-demo-a@example.com"
EMAIL_B = "atlas-demo-b@example.com"
HOST = "ep-spring-rice-az3v9osg.ap-southeast-1.aws.neon.tech"


def settings(**changes):
    base = dict(environment="production", staging_demo=True, cookie_secure=True,
                email_adapter="staging_sink", staging_transport_key=KEY,
                staging_mailbox_key=MAIL_KEY, staging_synthetic_emails=[EMAIL_A, EMAIL_B],
                frontend_url=FRONTEND, cors_origins=[FRONTEND], trusted_hosts=["demo-api.onrender.com"],
                session_hours=2, verification_minutes=10, reset_minutes=10,
                pool_size=1, pool_max_overflow=0, staging_database_host=HOST,
                database_url=f"postgresql+psycopg://atlas_staging_app@{HOST}/atlas_staging?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt")
    return Settings(_env_file=None, **(base | changes))


def client_for(config=None):
    app = create_app(config or settings(), engine=SimpleNamespace(connect=forbidden))
    return TestClient(app, base_url=BACKEND, headers={"Origin": FRONTEND, "X-Atlas-CSRF": "atlas", "X-Atlas-Staging-Key": KEY})


@pytest.mark.parametrize("change", [
    {"cookie_secure": False}, {"environment": "development"}, {"email_adapter": "preview"},
    {"staging_transport_key": "short"}, {"staging_mailbox_key": KEY},
    {"staging_synthetic_emails": ["real@gmail.com"]}, {"staging_synthetic_emails": []},
    {"staging_synthetic_emails": [EMAIL_A, EMAIL_A]}, {"pool_size": 2}, {"pool_max_overflow": 1},
    {"experimental_advisor": True}, {"enable_demo_seed": True},
    {"cors_origins": [FRONTEND, "https://other.onrender.com"]}, {"staging_signup_enabled": True},
    {"database_url": f"postgresql+psycopg://atlas_staging_owner@{HOST}/atlas_staging?sslmode=verify-full&sslrootcert=system"},
    {"database_url": f"postgresql+psycopg://atlas_staging_app@{HOST}/atlas?sslmode=verify-full&sslrootcert=system"},
    {"database_url": f"postgresql+psycopg://atlas_staging_app@{HOST}/atlas_staging?sslmode=require"},
    {"staging_database_host": "ep-spring-rice-az3v9osg-pooler.ap-southeast-1.aws.neon.tech"},
    {"trusted_hosts": ["localhost"]}, {"cookie_name": "other_session"},
    {"session_hours": 168}, {"verification_minutes": 1440},
])
def test_settings_fail_closed(change):
    with pytest.raises(ValidationError):
        settings(**change)


def test_staging_configuration_is_off_by_default_and_hides_input_errors():
    assert not Settings(_env_file=None).staging_demo
    with pytest.raises(ValidationError) as error:
        settings(staging_transport_key="SYNTHETIC-SECRET-SENTINEL")
    assert "SYNTHETIC-SECRET-SENTINEL" not in str(error.value)
    assert settings().pool_size == 1


@pytest.mark.parametrize("path", ["/api/v1/ready", "/api/v1/countries", "/api/v1/auth/me", "/api/v2/scholarships", "/docs", "/openapi.json"])
def test_direct_backend_rejected_before_database(path):
    with client_for() as c:
        assert c.get(path, headers={"X-Atlas-Staging-Key": "forged"}).status_code == 403


def test_health_is_public_and_does_not_use_database():
    with client_for() as c:
        response = c.get("/api/v1/health", headers={"X-Atlas-Staging-Key": ""})
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.parametrize("path,method", [("/api/v1/auth/me", "GET"), ("/api/v1/me/workspace", "GET"), ("/api/v1/auth/login", "POST")])
def test_write_authority_off_blocks_even_session_reads(path, method):
    with client_for() as c:
        assert c.request(method, path, json={}).status_code == 503


def test_signup_and_real_recipients_are_closed_before_database():
    with client_for(settings(staging_database_writes_enabled=True)) as c:
        assert c.post("/api/v1/auth/register", json={"email": EMAIL_A}).status_code == 403
        for path in ["login", "forgot-password", "resend-verification"]:
            assert c.post("/api/v1/auth/" + path, json={"email": "real@gmail.com"}).status_code == 403


@pytest.mark.parametrize("headers", [{"Origin": "https://evil.invalid"}, {"Origin": ""}, {"X-Atlas-CSRF": ""}])
def test_origin_and_csrf_still_required(headers):
    with client_for(settings(staging_database_writes_enabled=True)) as c:
        assert c.post("/api/v1/auth/login", json={"email": EMAIL_A}, headers=headers).status_code == 403


def test_mail_sink_never_uses_smtp_or_files(monkeypatch):
    monkeypatch.setattr("smtplib.SMTP", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    mailbox = StagingMailbox()
    deliver(settings(), EMAIL_A, "verification", "synthetic-placeholder", mailbox=mailbox)
    assert mailbox.consume(EMAIL_A, "verification") == FRONTEND + "/verify-email#token=synthetic-placeholder"
    assert mailbox.consume(EMAIL_A, "verification") is None
    with pytest.raises(ValueError):
        deliver(settings(), "real@gmail.com", "verification", "synthetic-placeholder", mailbox=mailbox)


def test_mail_is_bounded_expiring_and_lost_on_restart():
    clock = [0]
    mailbox = StagingMailbox(clock=lambda: clock[0])
    for i in range(16):
        mailbox.put(f"synthetic-{i}@example.com", "verification", "synthetic-link")
    with pytest.raises(ValueError):
        mailbox.put("overflow@example.com", "verification", "synthetic-link")
    clock[0] = 601
    assert mailbox.consume("synthetic-0@example.com", "verification") is None
    assert StagingMailbox().consume(EMAIL_A, "verification") is None


def test_operator_mail_requires_two_keys_origin_csrf_and_exact_recipient():
    with client_for() as c:
        c.app.state.staging_mailbox.put(EMAIL_A, "verification", FRONTEND + "/verify-email#token=synthetic-placeholder")
        path = "/api/v1/staging-mail/consume"
        assert c.post(path, json={"email": EMAIL_A}).status_code == 403
        assert c.post(path, json={"email": EMAIL_A}, headers={"X-Atlas-Mailbox-Key": MAIL_KEY, "X-Atlas-Staging-Key": "forged"}).status_code == 403
        assert c.post(path, json={"email": "real@gmail.com"}, headers={"X-Atlas-Mailbox-Key": MAIL_KEY}).status_code == 403
        response = c.post(path, json={"email": EMAIL_A}, headers={"X-Atlas-Mailbox-Key": MAIL_KEY})
        assert response.status_code == 200
        assert "#token=" in response.json()["link"]
        assert response.headers["Cache-Control"] == "no-store"
        assert c.post(path, json={"email": EMAIL_A}, headers={"X-Atlas-Mailbox-Key": MAIL_KEY}).status_code == 404


class MemoryDB:
    """Tiny persistence double; real PostgreSQL/session transaction behavior not certified."""
    def __init__(self):
        self.users = [User(id=uuid.uuid4(), email=email, password_hash="synthetic-hash", account_status="active") for email in [EMAIL_A, EMAIL_B]]
        self.sessions = []

    def scalar(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        parameters = statement.compile().params
        if entity is User:
            return next((u for u in self.users if ("email_1" in parameters and u.email == parameters["email_1"]) or ("id_1" in parameters and u.id == parameters["id_1"])), None)
        if entity is AuthSession:
            return next((s for s in self.sessions if s.token_hash == parameters.get("token_hash_1")), None)
        raise AssertionError("Unexpected synthetic query")

    def add(self, session):
        assert isinstance(session, AuthSession)
        session.id = uuid.uuid4()
        session.revoked_at = None
        session.last_used_at = now()
        self.sessions.append(session)

    def execute(self, statement):
        parameters = statement.compile().params
        for session in self.sessions:
            if session.token_hash == parameters.get("token_hash_1"):
                session.revoked_at = parameters["revoked_at"]

    def commit(self):
        pass

    def refresh(self, value):
        pass


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.setattr(auth, "throttle", lambda *args, **kwargs: None)
    monkeypatch.setattr(auth, "verify_password", lambda stored, candidate: stored == "synthetic-hash" and candidate == "Synthetic-password-111")
    monkeypatch.setattr(auth, "password_hasher", SimpleNamespace(check_needs_rehash=lambda value: False))
    db = MemoryDB()
    with client_for(settings(staging_database_writes_enabled=True)) as c:
        c.app.dependency_overrides[get_session] = lambda: db
        yield c, db


def login(c, email=EMAIL_A):
    result = c.post("/api/v1/auth/login", json={"email": email, "password": "Synthetic-password-111"})
    assert result.status_code == 200
    return result


def test_login_cookie_csrf_logout_and_session_revocation(auth_client):
    c, db = auth_client
    result = login(c)
    cookie = result.headers["set-cookie"].lower()
    for attribute in ["secure", "httponly", "samesite=lax", "path=/"]:
        assert attribute in cookie
    assert "domain=" not in cookie
    assert c.get("/api/v1/auth/me").json()["user"]["email"] == EMAIL_A
    assert c.post("/api/v1/auth/logout", headers={"X-Atlas-CSRF": "wrong"}).status_code == 403
    assert db.sessions[0].revoked_at is None
    logout = c.post("/api/v1/auth/logout", headers={"X-Atlas-CSRF": result.json()["csrf_token"]})
    assert logout.status_code == 200 and "Max-Age=0" in logout.headers["set-cookie"]
    assert db.sessions[0].revoked_at is not None
    assert c.get("/api/v1/auth/me").status_code == 401


def test_expired_session_is_rejected(auth_client):
    c, db = auth_client
    login(c)
    db.sessions[0].expires_at = now() - timedelta(seconds=1)
    assert c.get("/api/v1/auth/me").status_code == 401


def test_account_switch_rotates_cookie_and_revokes_old_session(auth_client):
    c, db = auth_client
    login(c)
    old = c.cookies.get("atlas_session")
    login(c, EMAIL_B)
    assert c.cookies.get("atlas_session") != old
    assert db.sessions[0].token_hash == digest(old) and db.sessions[0].revoked_at is not None
    assert c.get("/api/v1/auth/me").json()["user"]["email"] == EMAIL_B


def test_no_postgresql_or_smtp_connection_attempts():
    assert connection_attempts == []
