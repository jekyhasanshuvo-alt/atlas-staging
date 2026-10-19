from decimal import Decimal

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import (
    AcademicProgram,
    City,
    Country,
    LivingCostEstimate,
    Scholarship,
    ScholarshipProgram,
    University,
    VerificationRecord,
)
from app.schemas.catalog import Page, PageMeta
from app.services.serialization import financial_dto, scholarship_dto, university_dto


def annual_tuition():
    return case(
        (AcademicProgram.tuition_period == "year", AcademicProgram.tuition_amount),
        (AcademicProgram.tuition_period == "semester", AcademicProgram.tuition_amount * 2),
        (AcademicProgram.tuition_period == "month", AcademicProgram.tuition_amount * 12),
        (
            AcademicProgram.tuition_period == "degree",
            AcademicProgram.tuition_amount * 12 / AcademicProgram.duration_months,
        ),
    )


def escaped(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def page_result(session: Session, statement, page: int, page_size: int, serializer):
    total = (
        session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    )
    rows = session.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return Page(
        items=[serializer(row) for row in rows],
        meta=PageMeta(
            page=page, page_size=page_size, total=total, pages=(total + page_size - 1) // page_size
        ),
    )


def university_options():
    return [
        selectinload(University.country),
        selectinload(University.city),
        selectinload(University.verifications).selectinload(VerificationRecord.source),
        selectinload(University.programs)
        .selectinload(AcademicProgram.verifications)
        .selectinload(VerificationRecord.source),
        selectinload(University.programs)
        .selectinload(AcademicProgram.scholarship_links)
        .selectinload(ScholarshipProgram.scholarship),
    ]


def living_estimates(session: Session, city_ids: list[str]):
    if not city_ids:
        return {}
    return {
        cost.city_id: cost
        for cost in session.scalars(
            select(LivingCostEstimate)
            .join(City, LivingCostEstimate.city_id == City.id)
            .join(Country, City.country_id == Country.id)
            .where(
                LivingCostEstimate.city_id.in_(city_ids),
                LivingCostEstimate.currency == Country.currency_code,
            )
            .options(
                selectinload(LivingCostEstimate.verifications).selectinload(
                    VerificationRecord.source
                )
            )
            .order_by(LivingCostEstimate.id)
        ).all()
    }


def list_universities(
    session: Session,
    *,
    q="",
    country=None,
    city=None,
    degree=None,
    subject=None,
    max_tuition: Decimal | None = None,
    tuition_currency=None,
    scholarship=None,
    sort="name",
    page=1,
    page_size=12,
    ids=None,
):
    stmt = (
        select(University)
        .join(University.country)
        .join(University.city)
        .where(University.status == "active")
    )
    if q:
        term = "%" + escaped(q.strip()) + "%"
        stmt = stmt.where(
            or_(University.name.ilike(term, escape="\\"), City.name.ilike(term, escape="\\"))
        )
    if country:
        stmt = stmt.where(
            or_(Country.id == country, Country.iso_code == country.upper(), Country.name == country)
        )
    if city:
        stmt = stmt.where(or_(City.id == city, City.name == city))
    if ids is not None:
        stmt = stmt.where(University.id.in_(ids))
    # All program predicates share a single EXISTS, so degree and subject cannot match different programs.
    predicates = [AcademicProgram.university_id == University.id]
    if degree:
        predicates.append(AcademicProgram.degree_level == degree)
    if subject:
        predicates.append(AcademicProgram.field_of_study == subject)
    if tuition_currency:
        predicates.append(AcademicProgram.tuition_currency == tuition_currency)
    if max_tuition is not None:
        predicates.append(annual_tuition() <= max_tuition)
    linked = exists(
        select(ScholarshipProgram.program_id)
        .join(ScholarshipProgram.scholarship)
        .where(
            ScholarshipProgram.program_id == AcademicProgram.id,
            Scholarship.contract_version == 1,
        )
    )
    if scholarship is True:
        predicates.append(linked)
    elif scholarship is False:
        stmt = stmt.where(
            ~exists(
                select(AcademicProgram.id).where(
                    AcademicProgram.university_id == University.id, linked
                )
            )
        )
    if len(predicates) > 1:
        stmt = stmt.where(exists(select(AcademicProgram.id).where(and_(*predicates))))
    if sort == "tuition":
        tuition = select(func.min(annual_tuition())).where(
            AcademicProgram.university_id == University.id
        )
        if tuition_currency:
            tuition = tuition.where(AcademicProgram.tuition_currency == tuition_currency)
        ordering = tuition.correlate(University).scalar_subquery()
    elif sort == "living":
        ordering = (
            select(func.min(LivingCostEstimate.monthly_amount))
            .where(
                LivingCostEstimate.city_id == University.city_id,
                LivingCostEstimate.currency == tuition_currency,
            )
            .correlate(University)
            .scalar_subquery()
        )
    else:
        ordering = func.lower(University.name)
    stmt = stmt.order_by(ordering.asc().nulls_last(), University.id).options(*university_options())
    # Fetch a page, then resolve city references once for the page, not once per university.
    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = session.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    estimates = living_estimates(session, [u.city_id for u in rows])
    return Page(
        items=[university_dto(u, estimates.get(u.city_id)) for u in rows],
        meta=PageMeta(
            page=page, page_size=page_size, total=total, pages=(total + page_size - 1) // page_size
        ),
    )


def get_university(session: Session, identifier: str):
    u = session.scalar(
        select(University)
        .where(
            or_(University.id == identifier, University.slug == identifier),
            University.status == "active",
        )
        .options(*university_options())
    )
    return university_dto(u, living_estimates(session, [u.city_id]).get(u.city_id)) if u else None


def scholarship_options():
    return [
        selectinload(Scholarship.verifications).selectinload(VerificationRecord.source),
        selectinload(Scholarship.program_links)
        .selectinload(ScholarshipProgram.program)
        .selectinload(AcademicProgram.university)
        .selectinload(University.country),
    ]


def list_scholarships(
    session: Session,
    *,
    q="",
    country=None,
    degree=None,
    funding=None,
    page=1,
    page_size=12,
    ids=None,
):
    stmt = select(Scholarship).where(Scholarship.contract_version == 1)
    if q:
        term = "%" + escaped(q.strip()) + "%"
        stmt = stmt.where(
            or_(
                Scholarship.name.ilike(term, escape="\\"),
                Scholarship.description.ilike(term, escape="\\"),
            )
        )
    if ids is not None:
        stmt = stmt.where(Scholarship.id.in_(ids))
    if funding:
        stmt = stmt.where(Scholarship.funding_type == funding)
    if country or degree:
        relation = (
            select(ScholarshipProgram.program_id)
            .join(AcademicProgram)
            .join(University)
            .join(Country)
        )
        relation = relation.where(ScholarshipProgram.scholarship_id == Scholarship.id)
        if country:
            relation = relation.where(
                or_(
                    Country.id == country,
                    Country.iso_code == country.upper(),
                    Country.name == country,
                )
            )
        if degree:
            relation = relation.where(AcademicProgram.degree_level == degree)
        stmt = stmt.where(exists(relation))
    stmt = stmt.order_by(func.lower(Scholarship.name), Scholarship.id).options(
        *scholarship_options()
    )
    return page_result(session, stmt, page, page_size, scholarship_dto)


def get_scholarship(session: Session, identifier: str):
    row = session.scalar(
        select(Scholarship)
        .where(Scholarship.id == identifier, Scholarship.contract_version == 1)
        .options(*scholarship_options())
    )
    return scholarship_dto(row) if row else None


def financial_reference(session: Session, *, university_id=None, page=1, page_size=12):
    stmt = select(AcademicProgram).join(University).where(University.status == "active")
    if university_id:
        stmt = stmt.where(AcademicProgram.university_id == university_id)
    stmt = stmt.order_by(AcademicProgram.university_id, AcademicProgram.id).options(
        selectinload(AcademicProgram.verifications).selectinload(VerificationRecord.source),
        selectinload(AcademicProgram.scholarship_links).selectinload(
            ScholarshipProgram.scholarship
        ),
        selectinload(AcademicProgram.university).selectinload(University.country),
    )
    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = session.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    estimates = living_estimates(session, [p.university.city_id for p in rows])
    return Page(
        items=[financial_dto(p, estimates.get(p.university.city_id)) for p in rows],
        meta=PageMeta(
            page=page, page_size=page_size, total=total, pages=(total + page_size - 1) // page_size
        ),
    )
