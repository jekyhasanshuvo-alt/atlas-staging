"""Run with python -m app.cleanup; only expired authentication artifacts are removed."""

from datetime import timedelta

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import build_engine
from app.models.student import (
    AuthRateLimit,
    AuthSession,
    EmailVerificationToken,
    PasswordResetToken,
)
from app.services.security import now


def cleanup(db):
    cutoff = now() - timedelta(days=30)
    counts = {}
    for model, condition in [
        (AuthRateLimit, AuthRateLimit.expires_at < now()),
        (AuthSession, or_(AuthSession.expires_at < cutoff, AuthSession.revoked_at < cutoff)),
        (EmailVerificationToken, EmailVerificationToken.expires_at < cutoff),
        (PasswordResetToken, PasswordResetToken.expires_at < cutoff),
    ]:
        counts[model.__tablename__] = db.execute(delete(model).where(condition)).rowcount
    db.commit()
    return counts


if __name__ == "__main__":
    engine = build_engine(Settings())
    with Session(engine) as db:
        print(cleanup(db))
    engine.dispose()
