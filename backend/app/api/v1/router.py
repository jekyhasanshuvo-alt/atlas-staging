from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.catalog import Country
from app.repositories import catalog
from app.schemas.catalog import (
    CatalogOptionsDTO,
    CountryDTO,
    FinancialReferenceDTO,
    HealthDTO,
    Page,
    ReadyDTO,
    ScholarshipDTO,
    UniversityDTO,
)

router = APIRouter()
DB = Annotated[Session, Depends(get_session)]
PageNumber = Annotated[int, Query(ge=1, le=100000)]
PageSize = Annotated[int, Query(ge=1, le=100)]
ShortText = Annotated[str | None, Query(max_length=120)]
SearchText = Annotated[str, Query(max_length=200)]
Degree = Literal["Bachelor", "Master", "PhD"]


@router.get("/health", response_model=HealthDTO, tags=["system"])
def health():
    return {"status": "ok", "service": "atlas-api", "version": "0.2.0"}


@router.get("/ready", response_model=ReadyDTO, tags=["system"])
def ready(request: Request):
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database is unavailable") from None
    return {"status": "ready"}


@router.get("/countries", response_model=list[CountryDTO], tags=["catalog"])
def countries(session: DB):
    return [
        CountryDTO.model_validate(c)
        for c in session.scalars(select(Country).order_by(Country.name))
    ]


@router.get("/universities", response_model=Page[UniversityDTO], tags=["universities"])
def universities(
    session: DB,
    q: SearchText = "",
    country: ShortText = None,
    city: ShortText = None,
    degree: Degree | None = None,
    subject: ShortText = None,
    max_tuition: Annotated[Decimal | None, Query(ge=0, le=100000000)] = None,
    tuition_currency: Annotated[str | None, Query(pattern=r"^[A-Z]{3}$")] = None,
    scholarship: bool | None = None,
    sort: Literal["name", "tuition", "living"] = "name",
    page: PageNumber = 1,
    page_size: PageSize = 12,
    ids: Annotated[list[str] | None, Query(max_length=50)] = None,
):
    if (max_tuition is not None or sort != "name") and not tuition_currency:
        raise HTTPException(
            422,
            "A tuition_currency is required for cost filtering or sorting; no FX conversion is applied",
        )
    if ids is not None and any(len(value) > 120 for value in ids):
        raise HTTPException(422, "Identifiers must not exceed 120 characters")
    return catalog.list_universities(
        session,
        q=q,
        country=country,
        city=city,
        degree=degree,
        subject=subject,
        max_tuition=max_tuition,
        tuition_currency=tuition_currency,
        scholarship=scholarship,
        sort=sort,
        page=page,
        page_size=page_size,
        ids=ids,
    )


@router.get("/universities/{identifier}", response_model=UniversityDTO, tags=["universities"])
def university_detail(identifier: str, session: DB):
    result = catalog.get_university(session, identifier[:120]) if len(identifier) <= 120 else None
    if result is None:
        raise HTTPException(404, "University not found")
    return result


@router.get("/scholarships", response_model=Page[ScholarshipDTO], tags=["scholarships"])
def scholarships(
    session: DB,
    q: SearchText = "",
    country: ShortText = None,
    degree: Degree | None = None,
    funding: Literal["Full", "Partial"] | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 12,
    ids: Annotated[list[str] | None, Query(max_length=50)] = None,
):
    if ids is not None and any(len(value) > 120 for value in ids):
        raise HTTPException(422, "Identifiers must not exceed 120 characters")
    return catalog.list_scholarships(
        session,
        q=q,
        country=country,
        degree=degree,
        funding=funding,
        page=page,
        page_size=page_size,
        ids=ids,
    )


@router.get("/scholarships/{identifier}", response_model=ScholarshipDTO, tags=["scholarships"])
def scholarship_detail(identifier: str, session: DB):
    result = catalog.get_scholarship(session, identifier[:120]) if len(identifier) <= 120 else None
    if result is None:
        raise HTTPException(404, "Scholarship not found")
    return result


@router.get("/financial-reference", response_model=Page[FinancialReferenceDTO], tags=["finance"])
def financial_reference(
    session: DB, university_id: ShortText = None, page: PageNumber = 1, page_size: PageSize = 12
):
    return catalog.financial_reference(
        session, university_id=university_id, page=page, page_size=page_size
    )


@router.get("/catalog-options", response_model=CatalogOptionsDTO, tags=["catalog"])
def catalog_options(session: DB):
    from app.models.catalog import AcademicProgram, City, University
    from app.schemas.catalog import CityDTO

    subjects = session.scalars(
        select(AcademicProgram.field_of_study)
        .join(University)
        .where(University.status == "active")
        .distinct()
        .order_by(AcademicProgram.field_of_study)
    ).all()
    cities = session.scalars(select(City).order_by(City.name)).all()
    return CatalogOptionsDTO(
        subjects=list(subjects), cities=[CityDTO.model_validate(city) for city in cities]
    )
