from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.catalog import Page
from app.schemas.scholarship_public import ScholarshipPublic
from app.services.scholarship_public import matches, public_dto, visible_rows, visible_scholarship

router = APIRouter(prefix="/api/v2/scholarships", tags=["scholarships v2"])
Text = Annotated[str | None, Query(max_length=120)]


@router.get("", response_model=Page[ScholarshipPublic])
def scholarships(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    q: Annotated[str, Query(max_length=200)] = "",
    country: Text = None,
    university: Text = None,
    program: Text = None,
    degree: Literal["Bachelor", "Master", "PhD"] | None = None,
    intake: Text = None,
    provider: Text = None,
    funding: Literal["Full", "Partial"] | None = None,
    deadline_after: date | None = None,
    deadline_before: date | None = None,
    page: Annotated[int, Query(ge=1, le=100000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 12,
):
    if deadline_after and deadline_before and deadline_after > deadline_before:
        raise HTTPException(422, "Deadline range is reversed")
    rows = [
        r
        for r in visible_rows(session, request.app.state.settings)
        if matches(
            r,
            q=q,
            country=country,
            university=university,
            program=program,
            degree=degree,
            intake=intake,
            provider=provider,
            funding=funding,
            deadline_after=deadline_after,
            deadline_before=deadline_before,
        )
    ]
    return {
        "items": [public_dto(r) for r in rows[(page - 1) * page_size : page * page_size]],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": len(rows),
            "pages": (len(rows) + page_size - 1) // page_size,
        },
    }


@router.get("/{identifier}", response_model=ScholarshipPublic)
def detail(identifier: str, request: Request, session: Annotated[Session, Depends(get_session)]):
    row = (
        visible_scholarship(session, request.app.state.settings, identifier)
        if len(identifier) <= 36
        else None
    )
    if row is None:
        raise HTTPException(404, "Scholarship not found")
    return public_dto(row)
