from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings


def build_engine(settings: Settings):
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_timeout=5,
        pool_size=settings.pool_size,
        max_overflow=settings.pool_max_overflow,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=10000"},
    )


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
