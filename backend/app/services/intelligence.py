"""Read-only, period-preserving catalog discovery using existing review semantics."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.catalog import AcademicProgram, City, Country, University, VerificationRecord
from app.repositories.catalog import escaped
from app.schemas.catalog import CityDTO, CountryDTO, Page, PageMeta, SourceDTO
from app.schemas.curated import PROGRAM_FIELDS, UNIVERSITY_FIELDS, safe_url
from app.schemas.intelligence import Comparison, Fact, FieldEvidence, IntelligenceRecord
from app.services.review import attributed_fields, current_records
from app.services.serialization import provenance


def public_url(value):
    try:
        return safe_url(value)
    except ValueError:
        return None


def fact(entity, field):
    value = getattr(entity, field)
    if field == "official_website":
        value = public_url(value)
    relevant = [r for r in entity.verifications if r.review_field in (None, field)]
    status = provenance(relevant, entity.is_demo, {field}, entity).verification_status
    evidence = []
    now = datetime.now(UTC)
    for record in sorted(current_records(entity.verifications), key=lambda r: str(r.id)):
        if record.review_field != field and field not in attributed_fields(record):
            continue
        entry_status = provenance(
            [
                record,
                *[r for r in entity.verifications if r.review_field is None and r.id != record.id],
            ],
            entity.is_demo,
            {field},
            entity,
        ).verification_status
        source = SourceDTO.model_validate(record.source)
        source.source_url = public_url(source.source_url)
        # Future/unsupported decisions are not a last-reviewed claim.
        reviewed_at = record.reviewed_at if record.review_field == field else None
        if reviewed_at and reviewed_at > now:
            reviewed_at = None
        evidence.append(
            FieldEvidence(
                source=source,
                evidence_reference=f"{source.id}:{field}",
                verification_status=entry_status,
                reviewed_at=reviewed_at,
            )
        )
    caveat = (
        "Demo value; not factually verified."
        if entity.is_demo
        else (
            "Value unknown."
            if value is None or value == ""
            else "Review applies to this stored value; source age does not confirm the current intake."
        )
    )
    if field == "language_of_instruction":
        caveat += " Quoted teaching-language description; full-program language coverage is not established."
    return Fact(value=value, verification_status=status, evidence=evidence, caveat=caveat)


def dto(entity):
    is_program = isinstance(entity, AcademicProgram)
    university = entity.university if is_program else entity
    fields = PROGRAM_FIELDS if is_program else UNIVERSITY_FIELDS
    facts = {field: fact(entity, field) for field in sorted(fields)}
    for missing in ("intake", "admission_requirements"):
        facts[missing] = Fact(
            value=None,
            verification_status="unverified",
            evidence=[],
            caveat="Not represented in the current catalog schema; unknown.",
        )
    common = dict(
        id=entity.id,
        kind="program" if is_program else "university",
        name=entity.name,
        country=CountryDTO.model_validate(university.country),
        city=CityDTO.model_validate(university.city),
        is_demo=entity.is_demo,
        verification_status=provenance(
            entity.verifications, entity.is_demo, fields, entity
        ).verification_status,
        facts=facts,
    )
    if is_program:
        return IntelligenceRecord(
            **common,
            university_id=university.id,
            university_name=university.name,
            **{
                field: getattr(entity, field)
                for field in (
                    "degree_level",
                    "field_of_study",
                    "language_of_instruction",
                    "duration_months",
                    "tuition_amount",
                    "tuition_currency",
                    "tuition_period",
                )
            },
        )
    return IntelligenceRecord(
        **common,
        institution_type=entity.institution_type,
        official_website=public_url(entity.official_website),
        description=entity.description,
    )


def statement(kind, filters):
    model = AcademicProgram if kind == "programs" else University
    stmt = select(model)
    if model is AcademicProgram:
        stmt = stmt.join(AcademicProgram.university)
        stmt = stmt.options(
            selectinload(AcademicProgram.university).selectinload(University.country),
            selectinload(AcademicProgram.university).selectinload(University.city),
        )
    else:
        stmt = stmt.options(selectinload(University.country), selectinload(University.city))
    stmt = stmt.join(University.country).join(University.city).where(University.status == "active")
    stmt = stmt.options(selectinload(model.verifications).selectinload(VerificationRecord.source))
    if filters.get("ids") is not None:
        stmt = stmt.where(model.id.in_(filters["ids"]))
    for key, column in (("country", Country.iso_code), ("city", City.name)):
        if value := filters.get(key):
            alternatives = [column.ilike(escaped(value.strip()), escape="\\")]
            alternatives.append((Country.id if key == "country" else City.id) == value)
            if key == "country":
                alternatives.append(Country.name.ilike(escaped(value.strip()), escape="\\"))
            stmt = stmt.where(or_(*alternatives))
    for key, column in (
        ("q", model.name),
        ("name", model.name),
        ("institution_type", University.institution_type),
    ):
        if value := filters.get(key):
            pattern = escaped(value.strip())
            if key != "institution_type":
                pattern = "%" + pattern + "%"
            stmt = stmt.where(column.ilike(pattern, escape="\\"))
    predicates = []
    if value := filters.get("university"):
        stmt = stmt.where(
            or_(University.id == value, University.name.ilike(escaped(value.strip()), escape="\\"))
        )
    for key, column in (
        ("degree", AcademicProgram.degree_level),
        ("subject", AcademicProgram.field_of_study),
        ("language", AcademicProgram.language_of_instruction),
        ("tuition_currency", AcademicProgram.tuition_currency),
        ("tuition_period", AcademicProgram.tuition_period),
    ):
        if value := filters.get(key):
            # Teaching language is exact quoted text, never expanded to inferred English coverage.
            predicates.append(column.ilike(escaped(value.strip()), escape="\\"))
    for key, column, minimum in (
        ("min_tuition", AcademicProgram.tuition_amount, True),
        ("max_tuition", AcademicProgram.tuition_amount, False),
        ("min_duration", AcademicProgram.duration_months, True),
        ("max_duration", AcademicProgram.duration_months, False),
    ):
        if filters.get(key) is not None:
            predicates.append(column >= filters[key] if minimum else column <= filters[key])
    if predicates:
        if model is AcademicProgram:
            stmt = stmt.where(*predicates)
        else:
            stmt = stmt.where(
                select(AcademicProgram.id)
                .where(AcademicProgram.university_id == University.id, *predicates)
                .exists()
            )
    sort = filters.get("sort", "name")
    ordering = (
        AcademicProgram.tuition_amount
        if sort == "tuition"
        else (AcademicProgram.duration_months if sort == "duration" else func.lower(model.name))
    )
    return stmt.order_by(ordering.asc().nulls_last(), model.id)


def discover(session, kind, filters):
    stmt = statement(kind, filters)
    page, size = filters.get("page", 1), filters.get("page_size", 12)
    if status := filters.get("verification"):
        # Stored review flags cannot implement current fingerprint/expiry semantics.
        # Fail explicitly beyond the supported scan ceiling; never truncate totals.
        count = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
        if count > 5000:
            raise HTTPException(
                422, "Narrow filters before verification filtering (maximum 5000 candidates)"
            )
        items = []
        total = 0
        for offset in range(0, count, 100):
            for entity in session.scalars(stmt.offset(offset).limit(100)):
                fields = PROGRAM_FIELDS if kind == "programs" else UNIVERSITY_FIELDS
                if (
                    provenance(
                        entity.verifications, entity.is_demo, fields, entity
                    ).verification_status
                    == status
                ):
                    if (page - 1) * size <= total < page * size:
                        items.append(dto(entity))
                    total += 1
    else:
        total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
        items = [dto(row) for row in session.scalars(stmt.offset((page - 1) * size).limit(size))]
    return Page(
        items=items,
        meta=PageMeta(page=page, page_size=size, total=total, pages=(total + size - 1) // size),
    )


def compare(session, kind, ids):
    found = {row.id: dto(row) for row in session.scalars(statement(kind, {"ids": ids}))}
    return Comparison(
        items=[found[i] for i in ids if i in found],
        unavailable_ids=[i for i in ids if i not in found],
    )
