"""Fail before new-table/auth queries unless explicitly inside owned synthetic tests."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db.session import get_session


def require_foundation(request: Request, session=Depends(get_session)):
    settings = request.app.state.settings
    unavailable = HTTPException(
        503, "Experimental persistence is unavailable; schema and privacy approval are pending."
    )
    configured_url = make_url(settings.database_url.get_secret_value())
    bound_url = session.get_bind().engine.url
    target = configured_url.database or ""
    actual = bound_url.database or ""
    if not (
        settings.experimental_foundation
        and settings.environment == "test"
        and configured_url == bound_url
        and configured_url.host == "127.0.0.1"
        and configured_url.port == 55432
        and target == actual
        and target.startswith("atlas_phase9b_")
        and target.endswith("_test")
        and target not in {"atlas", "atlas_test"}
    ):
        raise unavailable
    identity = session.execute(
        text("SELECT current_database(), (SELECT version_num FROM alembic_version)")
    ).one()
    if identity != (target, "0005"):
        raise unavailable
    required = (
        "saved_programs",
        "student_academic_credentials",
        "student_language_credentials",
        "student_language_components",
        "student_study_preferences",
        "student_preference_choices",
    )
    if not all(
        session.scalar(text("SELECT to_regclass(:name) IS NOT NULL"), {"name": "public." + table})
        for table in required
    ):
        raise unavailable
