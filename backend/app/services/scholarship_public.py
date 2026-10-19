"""Bounded, default-deny publication; reviews alone never authorize publication."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.catalog import (
    AcademicProgram,
    Scholarship,
    ScholarshipScope,
    University,
    VerificationRecord,
)
from app.schemas.catalog import SourceDTO
from app.schemas.scholarship import term_document
from app.schemas.scholarship_public import PublicEvidence, ScholarshipPublic
from app.services.review import current_records, fingerprint
from app.services.serialization import scholarship_provenance


def publication_fingerprint(row):
    """Bind release approval to content, resolved destinations, captures and review heads."""
    terms = term_document(row).model_dump()
    terms["scopes"] = sorted(terms["scopes"], key=lambda s: s["id"])
    destinations = []
    for scope in sorted(row.scopes, key=lambda s: s.id):
        u = scope.university or (scope.program.university if scope.program else None)
        c = scope.country or (u.country if u else None)
        p = scope.program
        destinations.append(
            [
                scope.id,
                [c.id, c.name] if c else None,
                [u.id, u.name, u.status, u.is_demo] if u else None,
                [p.id, p.name, p.degree_level, p.is_demo] if p else None,
            ]
        )
    heads = sorted(current_records(row.verifications), key=lambda r: r.id)
    return fingerprint(
        {
            "publication_version": 1,
            "id": row.id,
            "terms": terms,
            "identity": [
                row.name,
                row.provider,
                row.description,
                row.eligibility_summary,
                row.coverage,
                row.official_url,
                row.funding_type,
            ],
            "destinations": destinations,
            "evidence": [
                [
                    r.id,
                    r.review_field,
                    r.value_fingerprint,
                    r.verification_status,
                    r.reviewed_at,
                    r.valid_from,
                    r.valid_until,
                    r.notes if r.review_field is None else None,
                    SourceDTO.model_validate(r.source).model_dump(),
                ]
                for r in heads
            ],
        }
    )


def candidates(session, settings):
    if not settings.published_scholarships:
        return []
    return session.scalars(
        select(Scholarship)
        .where(
            Scholarship.id.in_(settings.published_scholarships),
            Scholarship.contract_version == 2,
            Scholarship.is_demo.is_(False),
        )
        .order_by(Scholarship.name, Scholarship.id)
        .options(
            selectinload(Scholarship.verifications).selectinload(VerificationRecord.source),
            selectinload(Scholarship.scopes).selectinload(ScholarshipScope.country),
            selectinload(Scholarship.scopes)
            .selectinload(ScholarshipScope.university)
            .selectinload(University.country),
            selectinload(Scholarship.scopes)
            .selectinload(ScholarshipScope.program)
            .selectinload(AcademicProgram.university)
            .selectinload(University.country),
        )
    ).all()


def publishable(row):
    # Fail closed for invalid raw SQL terms, demo destinations and inactive institutions.
    try:
        for scope in row.scopes:
            university = scope.university or (scope.program.university if scope.program else None)
            if university and (university.is_demo or university.status != "active"):
                return False
            if scope.program and scope.program.is_demo:
                return False
        return scholarship_provenance(row).verification_status == "verified"
    except ValueError:
        return False


def public_dto(row):
    provenance = scholarship_provenance(row)
    labels = {}
    for scope in row.scopes:
        target = scope.country or scope.university or scope.program
        labels[scope.id] = target.name
        university = scope.university or (scope.program.university if scope.program else None)
        if university:
            labels["university:" + university.id] = university.name
        if scope.program:
            labels["program:" + scope.program.id] = scope.program.name
    return ScholarshipPublic(
        **term_document(row).model_dump(),
        **{
            key: getattr(row, key)
            for key in (
                "id",
                "name",
                "provider",
                "description",
                "eligibility_summary",
                "coverage",
                "official_url",
                "funding_type",
            )
        },
        verification_status=provenance.verification_status,
        evidence=[
            PublicEvidence(field=field, source=SourceDTO.model_validate(r.source))
            for r in provenance.records
            if r.verification_status == "verified"
            for field in r.reviewed_fields
        ],
        scope_labels=labels,
    )


def visible_rows(session, settings):
    return [
        row
        for row in candidates(session, settings)
        if publishable(row)
        and settings.published_scholarships.get(row.id) == publication_fingerprint(row)
    ]


def visible_scholarship(session, settings, identifier):
    if identifier not in settings.published_scholarships:
        return None
    return next((r for r in visible_rows(session, settings) if r.id == identifier), None)


def matches(
    row,
    *,
    q="",
    country=None,
    university=None,
    program=None,
    degree=None,
    intake=None,
    provider=None,
    funding=None,
    deadline_after=None,
    deadline_before=None,
):
    if q.casefold() not in (row.name + " " + row.provider + " " + row.description).casefold():
        return False
    if provider and provider.casefold() not in row.provider.casefold():
        return False
    if intake and intake.casefold() not in (row.intake_label or "").casefold():
        return False
    if funding and row.funding_type != funding:
        return False
    if country or university or program or degree:

        def scope_matches(scope):
            u = scope.university or (scope.program.university if scope.program else None)
            c = scope.country or (u.country if u else None)
            return (
                (
                    not country
                    or (
                        c
                        and country.casefold()
                        in {c.id.casefold(), c.iso_code.casefold(), c.name.casefold()}
                    )
                )
                and (not university or (u and u.id == university))
                and (not program or scope.program_id == program)
                and (
                    not degree
                    or (
                        scope.degree_level
                        or (scope.program.degree_level if scope.program else None)
                    )
                    == degree
                )
            )

        if not any(scope_matches(s) for s in row.scopes):
            return False
    if deadline_after or deadline_before:
        days = [
            d.date or d.closes_at.date()
            for d in term_document(row).deadlines.values()
            if d.deadline_state == "known"
        ]
        if not any(
            (not deadline_after or d >= deadline_after)
            and (not deadline_before or d <= deadline_before)
            for d in days
        ):
            return False
    return True
