import hashlib
import hmac
import logging
import time
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.session import get_session
from app.models.student import AuthRateLimit, AuthSession, User

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
dummy_hash = password_hasher.hash("unused constant timing password 1876")
audit = logging.getLogger("atlas.security")


def now():
    return datetime.now(UTC)


def digest(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(raw: str):
    return digest("atlas-csrf:" + raw)


def verify_password(encoded: str, password: str):
    try:
        return password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def throttle(request: Request, db, action: str, email: str = "", commit: bool = True):
    settings = request.app.state.settings
    window = int(time.time()) // settings.rate_window_seconds
    # Both aggregate peer and per-identity limits; raw addresses/emails are not stored.
    identities = [request.client.host if request.client else "unknown"]
    if email:
        identities.append(email)
    for identity in identities:
        statement = insert(AuthRateLimit).values(
            key=digest(action + ":" + identity),
            window=window,
            count=1,
            expires_at=now() + timedelta(seconds=settings.rate_window_seconds * 2),
        )
        count = db.scalar(
            statement.on_conflict_do_update(
                index_elements=[AuthRateLimit.key, AuthRateLimit.window],
                set_={"count": AuthRateLimit.count + 1},
            ).returning(AuthRateLimit.count)
        )
        if commit:
            db.commit()  # Failed authentication attempts must still consume their budget.
        if count > settings.rate_limit:
            db.commit()
            audit.info("event=rate_limit action=%s", action)
            raise HTTPException(429, "Too many requests. Please try again later.")


def authenticated(request: Request, db=Depends(get_session)):
    raw = request.cookies.get(request.app.state.settings.cookie_name, "")
    if not 40 <= len(raw) <= 100:
        raise HTTPException(401, "Sign in to continue.")
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest(raw)))
    if session is None:
        raise HTTPException(401, "Your session has expired. Sign in again.")
    # Serialize all private operations with deletion/reset; re-read after obtaining lock.
    user = db.scalar(select(User).where(User.id == session.user_id).with_for_update())
    if user is None:
        raise HTTPException(401, "Your session has expired. Sign in again.")
    db.refresh(session)
    if (
        user is None
        or user.account_status != "active"
        or session.revoked_at
        or session.expires_at <= now()
    ):
        raise HTTPException(401, "Your session has expired. Sign in again.")
    settings = request.app.state.settings
    if settings.staging_demo and user.email not in settings.staging_synthetic_emails:
        raise HTTPException(403, "This account is unavailable in the synthetic demo.")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not hmac.compare_digest(
        request.headers.get("X-Atlas-CSRF", "").encode("utf-8"), csrf_token(raw).encode("ascii")
    ):
        raise HTTPException(403, "Invalid CSRF token. Refresh and try again.")
    session.last_used_at = now()
    request.state.auth_session = session
    return user


def verified(user=Depends(authenticated)):
    if user.email_verified_at is None:
        raise HTTPException(403, "Verify your email before opening your student workspace.")
    return user
