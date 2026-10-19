from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db.session import get_session


def require_journey(request: Request, db=Depends(get_session)):
    settings = request.app.state.settings
    configured = make_url(settings.database_url.get_secret_value())
    actual = db.get_bind().engine.url
    unavailable = HTTPException(
        503, "Application tracking is not available; schema and privacy approval are pending."
    )
    if not (
        settings.experimental_journey
        and settings.environment == "test"
        and configured == actual
        and configured.host == "127.0.0.1"
        and configured.port == 55432
        and (configured.database or "").startswith("atlas_phase10_")
        and configured.database.endswith("_test")
    ):
        raise unavailable
    if db.execute(
        text("SELECT current_database(), (SELECT version_num FROM alembic_version)")
    ).one() != (configured.database, "0006"):
        raise unavailable
    if not all(
        db.scalar(text("SELECT to_regclass(:table) IS NOT NULL"), {"table": "public." + table})
        for table in ("student_applications", "application_status_events", "application_items")
    ):
        raise unavailable
