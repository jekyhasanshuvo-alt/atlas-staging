"""Deterministic private comparisons. No fabricated admissions rules or persisted assessments."""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.catalog import AcademicProgram, University, VerificationRecord
from app.schemas.catalog import PageMeta
from app.schemas.profile_intelligence import (
    Assessment,
    Completeness,
    CompletenessDimension,
    EligibilityCheck,
    Match,
    MatchPage,
    PreferenceReason,
)
from app.services.intelligence import dto, fact, statement

DISCLAIMER = "Stored-value preference comparison only. Admission, scholarship eligibility and visa approval are not established."


def supplied(profile, field):
    value = getattr(profile, field, None) if profile is not None else None
    return value.strip() if isinstance(value, str) and value.strip() else None


def completeness(profile):
    fields = {
        "full_name": "Name",
        "nationality": "Nationality",
        "current_country": "Current country",
        "education_level": "Current education level",
        "academic_background": "Academic background text",
        "language_proficiency": "Language self-report",
        "preferred_destination": "Preferred destination",
        "preferred_subject": "Study interest",
        "career_goals": "Career goals",
    }
    dimensions = [
        CompletenessDimension(
            field=field,
            label=label,
            status="PROVIDED" if supplied(profile, field) else "MISSING",
            explanation="Presence of self-reported text only; not document or academic verification.",
        )
        for field, label in fields.items()
    ]
    budget = (
        profile is not None
        and profile.budget_amount > 0
        and profile.budget_currency in {"CNY", "USD", "BDT"}
    )
    dimensions.append(
        CompletenessDimension(
            field="budget",
            label="Budget amount and currency",
            status="PROVIDED" if budget else "MISSING",
            explanation="A default zero/currency is not a chosen budget. Its period is not stored; select one explicitly for a comparison.",
        )
    )
    for field, label in {
        "qualifications": "Structured qualification awards",
        "grades": "Grades and grading system",
        "language_tests": "Language test scores and dates",
        "preferred_degree": "Saved preferred degree",
        "teaching_language_preference": "Saved teaching-language preference",
        "budget_period": "Saved budget period",
    }.items():
        dimensions.append(
            CompletenessDimension(
                field=field,
                label=label,
                status="UNSUPPORTED",
                explanation="No structured profile column exists; not inferred from other text or defaults.",
            )
        )
    return Completeness(
        provided=sum(d.status == "PROVIDED" for d in dimensions),
        supported=10,
        dimensions=dimensions,
        explanation="Counts supplied supported fields, not admission readiness or verified qualifications. Unsupported fields are excluded; the default scholarship checkbox is not scored.",
    )


def normalized(value):
    return " ".join(value.split()).casefold() if value else ""


def context(program, fields):
    facts = [
        fact(program.university, "country_id") if field == "destination" else fact(program, field)
        for field in fields
    ]
    statuses = {entry.verification_status for entry in facts}
    status = next(
        (s for s in ("rejected", "stale", "under_review", "unverified") if s in statuses),
        "verified",
    )
    evidence = {}
    for entry in facts:
        for item in entry.evidence:
            previous = evidence.get(item.evidence_reference)
            if previous is None or (
                item.reviewed_at
                and (not previous.reviewed_at or item.reviewed_at > previous.reviewed_at)
            ):
                evidence[item.evidence_reference] = item
    return status, list(evidence.values())


def preference_reasons(profile, program, options):
    reasons = []

    def compare(attribute, requested, value, fields, *, alternatives=()):
        status, evidence = context(program, fields)
        outcome = (
            "NOT_SET"
            if not requested
            else "UNKNOWN"
            if not value
            else (
                "MATCH"
                if normalized(requested) in {normalized(v) for v in (value, *alternatives)}
                else "DIFFERENT"
            )
        )
        reasons.append(
            PreferenceReason(
                attribute=attribute,
                outcome=outcome,
                input_used=requested,
                program_value=value,
                logic="Exact comparison after whitespace/case normalization; no semantic, qualification or eligibility inference.",
                uncertainty="Comparison uses stored values. Confirm unverified, stale, rejected or demo facts. Language text does not establish full-program language coverage.",
                catalog_verification=status,
                evidence=evidence,
            )
        )

    country = program.university.country
    compare(
        "destination",
        supplied(profile, "preferred_destination"),
        country.name,
        ["destination"],
        alternatives=(country.id, country.iso_code),
    )
    compare(
        "study_interest",
        supplied(profile, "preferred_subject"),
        program.field_of_study,
        ["field_of_study"],
    )
    compare("degree", options.preferred_degree, program.degree_level, ["degree_level"])
    compare(
        "teaching_language",
        options.teaching_language,
        program.language_of_instruction,
        ["language_of_instruction"],
    )
    status, evidence = context(program, ["tuition_amount", "tuition_currency", "tuition_period"])
    amount = profile.budget_amount if profile is not None else Decimal(0)
    currency = supplied(profile, "budget_currency")
    program_value = (
        None
        if program.tuition_amount is None
        else f"{program.tuition_amount} {program.tuition_currency} / {program.tuition_period}"
    )
    input_used = (
        f"{amount} {currency or 'currency unknown'} / {options.budget_period or 'period unknown'}"
        if amount > 0
        else None
    )
    outcome, logic = (
        "NOT_SET",
        "No usable budget supplied; default zero does not mean a zero-cost requirement.",
    )
    if amount > 0:
        if (
            program.tuition_amount is None
            or not options.budget_period
            or currency != program.tuition_currency
            or options.budget_period != program.tuition_period
        ):
            outcome, logic = (
                "UNKNOWN",
                "Compare only a known tuition amount with the exact original currency AND explicitly chosen period. No FX or annualization.",
            )
        else:
            outcome = "MATCH" if program.tuition_amount <= amount else "DIFFERENT"
            logic = "Stored tuition <= explicitly comparable budget ceiling; equality is included."
    reasons.append(
        PreferenceReason(
            attribute="tuition_reference_budget",
            outcome=outcome,
            input_used=input_used,
            program_value=program_value,
            logic=logic,
            catalog_verification=status,
            evidence=evidence,
            uncertainty="Budget period is temporary, not saved. Tuition-only comparison excludes living costs, undocumented conditions and other fees; it does not establish financial sufficiency. No scholarship deduction.",
        )
    )
    return reasons


def preference_result(reasons):
    outcomes = [r.outcome for r in reasons if r.outcome != "NOT_SET"]
    return (
        "DIFFERS"
        if "DIFFERENT" in outcomes
        else "UNKNOWN"
        if not outcomes or "UNKNOWN" in outcomes
        else "MATCHES"
    )


def eligibility_checks(profile):
    inputs = {
        "academic": {
            "education_level": supplied(profile, "education_level"),
            "academic_background": "Self-report text present; not parsed"
            if supplied(profile, "academic_background")
            else None,
            "structured_qualifications": None,
            "grades": None,
        },
        "language": {
            "language_proficiency": "Self-report text present; not parsed"
            if supplied(profile, "language_proficiency")
            else None,
            "structured_tests": None,
        },
        "nationality": {"nationality": supplied(profile, "nationality")},
        "documents": {"structured_documents": None},
        "intake": {"chosen_admissions_round": None},
    }
    return [
        EligibilityCheck(
            category=kind,
            status="NOT_ASSESSED",
            requirement=f"Structured, program-and-intake-specific {kind} requirements are unavailable.",
            student_input_used=value,
            official_requirement_source=None,
            comparison_logic="No admissions comparison performed: no modeled requirement and valid exact-cycle requirement evidence.",
            uncertainty="Self-reports, catalog descriptions and preference matches cannot establish eligibility. No grading conversion or nationality assumption is made.",
        )
        for kind, value in inputs.items()
    ]


def program_statement(filters):
    return statement("programs", filters).options(
        selectinload(AcademicProgram.university)
        .selectinload(University.verifications)
        .selectinload(VerificationRecord.source)
    )


def assess(session, profile, identifier, options):
    program = session.scalar(program_statement({"ids": [identifier]}))
    if program is None:
        raise HTTPException(404, "Program is unavailable.")
    reasons = preference_reasons(profile, program, options)
    return Assessment(
        program=dto(program),
        preference_result=preference_result(reasons),
        reasons=reasons,
        explanation=DISCLAIMER,
        eligibility_checks=eligibility_checks(profile),
    )


def matches(session, profile, query):
    stmt = program_statement({"q": query.q, "university": query.university})
    count = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    if count > 1000:
        raise HTTPException(422, "Narrow search filters before matching (maximum 1000 candidates).")
    items, total = [], 0
    for offset in range(0, count, 100):
        for program in session.scalars(stmt.offset(offset).limit(100)):
            public = dto(program)
            if query.verification and public.verification_status != query.verification:
                continue
            reasons = preference_reasons(profile, program, query)
            result = preference_result(reasons)
            if query.preference_result != "all" and result != query.preference_result:
                continue
            if (query.page - 1) * query.page_size <= total < query.page * query.page_size:
                items.append(
                    Match(
                        program=public,
                        preference_result=result,
                        reasons=reasons,
                        explanation=DISCLAIMER,
                    )
                )
            total += 1
    return MatchPage(
        items=items,
        meta=PageMeta(
            page=query.page,
            page_size=query.page_size,
            total=total,
            pages=(total + query.page_size - 1) // query.page_size,
        ),
        explanation=DISCLAIMER,
    )
