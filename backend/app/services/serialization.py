from datetime import UTC, datetime

from app.models.catalog import (
    AcademicProgram,
    LivingCostEstimate,
    Scholarship,
    University,
    VerificationRecord,
)
from app.schemas.catalog import (
    CityDTO,
    CostDTO,
    CountryDTO,
    FinancialReferenceDTO,
    ProgramDTO,
    ProvenanceDTO,
    ScholarshipDTO,
    SourceDTO,
    UniversityDTO,
    VerificationDTO,
)
from app.services.review import current_records, field_supported, value_fingerprint


def provenance(
    records: list[VerificationRecord], is_demo: bool, required: set[str], entity=None
) -> ProvenanceDTO:
    now = datetime.now(UTC)
    entries = []
    reviewed = set()
    statuses = []
    for r in current_records(records):
        status = r.verification_status
        if r.valid_until and r.valid_until < now:
            status = "stale"
        if r.valid_from and r.valid_from > now:
            status = "under_review"
        fields = [field.strip() for field in r.reviewed_fields.split(",") if field.strip()]
        if entity is not None:
            if r.review_field is None:
                status = "unverified"
            elif not field_supported(entity, r.source, r.review_field, records, now):
                status = "unverified"
            elif r.value_fingerprint != value_fingerprint(entity, r.source, r.review_field):
                status = "stale"
        elif r.source.source_type == "demo":
            status = "unverified"
        if status == "verified":
            reviewed.update(fields)
        statuses.append(status)
        target = next(
            (kind, identifier)
            for kind, identifier in [
                ("university", r.university_id),
                ("program", r.program_id),
                ("scholarship", r.scholarship_id),
                ("living_estimate", r.living_estimate_id),
            ]
            if identifier
        )
        entries.append(
            VerificationDTO(
                entity_type=target[0],
                entity_id=target[1],
                verification_status=status,
                reviewed_at=r.reviewed_at,
                reviewed_fields=fields,
                valid_from=r.valid_from,
                valid_until=r.valid_until,
                notes="",  # Preserve the v1 shape without exposing private review/audit notes.
                source=SourceDTO.model_validate(r.source),
            )
        )
    status = "unverified"
    if not is_demo:
        if "rejected" in statuses:
            status = "rejected"
        elif "stale" in statuses:
            status = "stale"
        elif required <= reviewed:
            status = "verified"
        elif "verified" in statuses or "under_review" in statuses:
            status = "under_review"
    return ProvenanceDTO(is_demo=is_demo, verification_status=status, records=entries)


def living_dto(estimate: LivingCostEstimate | None):
    if estimate is None:
        return None
    return CostDTO(
        amount=estimate.monthly_amount,
        currency=estimate.currency,
        period="month",
        provenance=provenance(
            estimate.verifications, estimate.is_demo, {"monthly_amount", "currency"}
        ),
    )


def program_dto(program: AcademicProgram):
    return ProgramDTO(
        id=program.id,
        name=program.name,
        degree_level=program.degree_level,
        field_of_study=program.field_of_study,
        language_of_instruction=program.language_of_instruction,
        duration_months=program.duration_months,
        tuition_amount=program.tuition_amount,
        tuition_currency=program.tuition_currency,
        tuition_period=program.tuition_period,
        scholarship_ids=sorted(
            link.scholarship_id
            for link in program.scholarship_links
            if link.scholarship.contract_version == 1
        ),
        provenance=provenance(
            program.verifications,
            program.is_demo,
            {
                "name",
                "degree_level",
                "field_of_study",
                "language_of_instruction",
                "duration_months",
                "tuition_amount",
                "tuition_currency",
                "tuition_period",
            },
            entity=program,
        ),
    )


def university_dto(u: University, estimate: LivingCostEstimate | None):
    return UniversityDTO(
        id=u.id,
        slug=u.slug,
        name=u.name,
        short_name=u.short_name,
        color=u.color,
        country=CountryDTO.model_validate(u.country),
        city=CityDTO.model_validate(u.city),
        official_website=u.official_website,
        description=u.description,
        institution_type=u.institution_type,
        status=u.status,
        programs=[program_dto(p) for p in u.programs],
        living_cost=living_dto(estimate),
        provenance=provenance(
            u.verifications,
            u.is_demo,
            {
                "name",
                "country_id",
                "city_id",
                "description",
                "institution_type",
                "official_website",
            },
            entity=u,
        ),
    )


def scholarship_dto(s: Scholarship):
    countries = {
        link.program.university.country.id: link.program.university.country
        for link in s.program_links
    }
    return ScholarshipDTO(
        id=s.id,
        name=s.name,
        provider=s.provider,
        description=s.description,
        funding_type=s.funding_type,
        funding_amount=s.funding_amount,
        funding_currency=s.funding_currency,
        eligibility_summary=s.eligibility_summary,
        application_deadline=s.application_deadline,
        official_url=s.official_url,
        coverage=s.coverage,
        countries=[CountryDTO.model_validate(countries[key]) for key in sorted(countries)],
        degree_levels=sorted({link.program.degree_level for link in s.program_links}),
        program_ids=sorted(link.program_id for link in s.program_links),
        provenance=provenance(
            s.verifications,
            s.is_demo,
            {
                "name",
                "provider",
                "funding_type",
                "funding_amount",
                "funding_currency",
                "eligibility_summary",
                "application_deadline",
                "official_url",
                "coverage",
            },
            entity=s if any(r.review_field is not None for r in s.verifications) else None,
        ),
    )


def scholarship_provenance(s: Scholarship):
    """Internal structured provenance; no new public API or legacy DTO coercion."""
    from app.schemas.scholarship import SCALAR_FIELDS, term_document

    terms = term_document(s).model_dump(mode="json")
    required = {field for field in SCALAR_FIELDS if getattr(s, field, None) is not None}
    for root in ("benefits", "requirements", "deadlines", "scopes"):
        children = terms[root] or {}
        if root == "scopes":
            children = {row["id"]: row for row in children}
        for key, child in children.items():
            required.update(
                f"{root}.{key}.{field}"
                for field, value in child.items()
                if field != "id" and value is not None
            )
    # Unknown critical terms cannot be converted into full verification by reviewing
    # the word 'unknown'. These sentinels are never valid review paths.
    if (
        terms["cycle_state"] != "known"
        or terms["applicability_state"] not in {"listed", "unrestricted"}
        or not terms["benefits"]
        or not terms["requirements"]
        or not terms["deadlines"]
    ):
        required.add("!incomplete")
    if any(
        b["value_state"] == "unknown" or b["condition_state"] == "unknown"
        for b in (terms["benefits"] or {}).values()
    ):
        required.add("!incomplete")
    if any(d["deadline_state"] == "unknown" for d in (terms["deadlines"] or {}).values()):
        required.add("!incomplete")
    if not any(
        r["category"] == "nationality" and r["nationality_mode"] != "unknown"
        for r in (terms["requirements"] or {}).values()
    ):
        required.add("!incomplete")
    return provenance(s.verifications, s.is_demo, required, entity=s)


def financial_dto(p: AcademicProgram, estimate: LivingCostEstimate | None):
    return FinancialReferenceDTO(
        program_id=p.id,
        university_id=p.university_id,
        university_name=p.university.name,
        country=CountryDTO.model_validate(p.university.country),
        program_name=p.name,
        tuition_amount=p.tuition_amount,
        tuition_currency=p.tuition_currency,
        tuition_period=p.tuition_period,
        duration_months=p.duration_months,
        provenance=program_dto(p).provenance,
        living_cost=living_dto(estimate),
    )
