from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.student import StudentProfile
from app.schemas.profile_intelligence import (
    Assessment,
    AssessmentOptions,
    Completeness,
    MatchingQuery,
    MatchPage,
)
from app.services import profile_intelligence as intelligence
from app.services.security import verified

router = APIRouter(prefix="/api/v1/me/intelligence", tags=["private profile intelligence"])
DB = Annotated[Session, Depends(get_session)]
Current = Annotated[object, Depends(verified)]


@router.get("/completeness", response_model=Completeness)
def completeness(user: Current, session: DB):
    return intelligence.completeness(session.get(StudentProfile, user.id))


@router.post("/matches", response_model=MatchPage)
def matches(query: MatchingQuery, user: Current, session: DB):
    return intelligence.matches(session, session.get(StudentProfile, user.id), query)


@router.post("/assessments/{identifier}", response_model=Assessment)
def assessment(
    identifier: Annotated[str, Path(min_length=1, max_length=36)],
    options: AssessmentOptions,
    user: Current,
    session: DB,
):
    return intelligence.assess(session, session.get(StudentProfile, user.id), identifier, options)
