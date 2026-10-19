"""Default absent; current-session checked without auth bookkeeping or chat writes."""

import hmac
import time
from collections import OrderedDict, deque
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.advisor.retrieval import CatalogRetriever
from app.advisor.schemas import Answer, Ask
from app.advisor.service import answer, compose
from app.db.session import get_session
from app.models.student import AuthSession, User
from app.services.security import csrf_token, digest, now

router = APIRouter(prefix="/api/v1/advisor", tags=["synthetic offline advisor"])


def require_advisor(request: Request, db=Depends(get_session)):
    s = request.app.state.settings
    u = make_url(s.database_url.get_secret_value())
    if not (
        s.experimental_advisor
        and s.environment == "test"
        and u == db.get_bind().engine.url
        and u.host == "127.0.0.1"
        and u.port == 55432
        and (u.database or "").startswith("atlas_phase11_")
        and u.database.endswith("_test")
    ):
        raise HTTPException(
            503, "Offline advisor is unavailable; synthetic-only approval required."
        )
    db.execute(text("SET TRANSACTION READ ONLY"))
    if db.execute(
        text("SELECT current_database(),(SELECT version_num FROM alembic_version)")
    ).one() != (u.database, "0004"):
        raise HTTPException(503, "Offline advisor database identity/revision mismatch.")
    raw = request.cookies.get(s.cookie_name, "")
    if not 40 <= len(raw) <= 100:
        raise HTTPException(401, "Sign in to continue.")
    auth = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest(raw)))
    user = db.get(User, auth.user_id) if auth else None
    if (
        not auth
        or not user
        or user.account_status != "active"
        or auth.revoked_at
        or auth.expires_at <= now()
    ):
        raise HTTPException(401, "Session unavailable.")
    if user.email_verified_at is None:
        raise HTTPException(403, "Verify your email first.")
    if request.method == "POST" and not hmac.compare_digest(
        request.headers.get("X-Atlas-CSRF", ""), csrf_token(raw)
    ):
        raise HTTPException(403, "Invalid CSRF token.")
    return digest(raw)


class Quota:
    def __init__(self):
        self.rows = OrderedDict()
        self.lock = Lock()

    def consume(self, key, instant=None):
        instant = time.monotonic() if instant is None else instant
        with self.lock:
            values = self.rows.pop(key, deque())
            while values and values[0] <= instant - 60:
                values.popleft()
            if len(values) >= 20:
                self.rows[key] = values
                raise HTTPException(429, "Offline advisor quota exceeded; retry after one minute.")
            values.append(instant)
            self.rows[key] = values
            while len(self.rows) > 512:
                self.rows.popitem(last=False)


@router.get("/capabilities")
def capabilities(identity=Depends(require_advisor)):
    return {
        "available": True,
        "provider": "offline_rules_v1",
        "external_inference": False,
        "conversation_stored": False,
        "private_context": "explicit_request_only",
        "operational_journey": False,
        "eligibility_status": "NOT_ASSESSED",
    }


@router.post("/ask", response_model=Answer)
def ask(data: Ask, request: Request, identity=Depends(require_advisor), db=Depends(get_session)):
    request.app.state.advisor_quota.consume(identity)
    try:
        return compose(data, CatalogRetriever(db, request.app.state.settings))
    except Exception:
        # Do not log raw prompts, provider payloads or private SQL/exception strings.
        return answer(
            "INTERNAL_ERROR",
            "ADVISOR_INTERNAL",
            data.intent,
            "The offline advisor could not complete this request. No conversation was saved.",
        )
