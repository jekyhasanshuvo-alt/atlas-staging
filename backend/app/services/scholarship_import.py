"""Create-only scholarship planning/apply, sharing the existing importer transaction contract."""

from sqlalchemy import or_, select, tuple_

from app.models.catalog import (
    AcademicProgram,
    Country,
    DataSource,
    Scholarship,
    ScholarshipProgram,
    ScholarshipScope,
    University,
    VerificationRecord,
)
from app.schemas.scholarship import ScopeInput
from app.services.curated_import import ImportConflict, ImportPlan, evidence_values


def scholarship_values(record):
    values = record.model_dump(exclude={"scopes"})
    for key in ("benefits", "requirements", "deadlines"):
        values[key] = record.model_dump(mode="json")[key]
    return {**values, "is_demo": False}


def preview_scholarship_import(session, batch):
    plan = ImportPlan()

    def conflict(kind, identifier, reason):
        plan.conflicts.append({"entity": kind, "id": identifier, "reason": reason})

    def classify(kind, model, identifier, values, existing):
        if existing is None:
            plan.created.append({"entity": kind, "id": identifier})
            plan.rows.append((model, values))
        elif getattr(existing, "is_demo", False) or (
            model is DataSource and existing.source_type == "demo"
        ):
            conflict(kind, identifier, "Existing demo record cannot be imported or overwritten")
        elif any(getattr(existing, k) != v for k, v in values.items()):
            conflict(kind, identifier, "Existing content differs")
        else:
            plan.unchanged.append({"entity": kind, "id": identifier})

    with session.no_autoflush:
        sources = {
            r.id: r
            for r in session.scalars(
                select(DataSource).where(DataSource.id.in_([s.id for s in batch.sources]))
            )
        }
        scholarships = {
            r.id: r
            for r in session.scalars(
                select(Scholarship).where(
                    or_(
                        Scholarship.id.in_([s.id for s in batch.scholarships]),
                        tuple_(Scholarship.scheme_key, Scholarship.round_key).in_(
                            [(s.scheme_key, s.round_key) for s in batch.scholarships]
                        ),
                    )
                )
            )
        }
        rounds = {(s.scheme_key, s.round_key): s.id for s in scholarships.values()}
        scope_ids = [scope.id for row in batch.scholarships for scope in row.scopes]
        scopes = {
            s.id: s
            for s in session.scalars(
                select(ScholarshipScope).where(ScholarshipScope.id.in_(scope_ids))
            )
        }
        for source in batch.sources:
            classify("source", DataSource, source.id, source.model_dump(), sources.get(source.id))
        for record in batch.scholarships:
            owner = rounds.get((record.scheme_key, record.round_key))
            if owner is not None and owner != record.id:
                conflict("scholarship", record.id, "Scheme/round belongs to another scholarship")
            existing = scholarships.get(record.id)
            classify("scholarship", Scholarship, record.id, scholarship_values(record), existing)
            expected_scopes = sorted([s.model_dump() for s in record.scopes], key=lambda s: s["id"])
            expected_programs = {s.program_id for s in record.scopes if s.program_id}
            if existing is not None:
                actual_scopes = sorted(
                    [{k: getattr(s, k) for k in ScopeInput.model_fields} for s in existing.scopes],
                    key=lambda s: s["id"],
                )
                if (
                    actual_scopes != expected_scopes
                    or {link.program_id for link in existing.program_links} != expected_programs
                ):
                    conflict(
                        "scholarship", record.id, "Existing scope or program projection differs"
                    )
            for scope in record.scopes:
                model, identifier = next(
                    (m, i)
                    for m, i in [
                        (Country, scope.country_id),
                        (University, scope.university_id),
                        (AcademicProgram, scope.program_id),
                    ]
                    if i is not None
                )
                target = session.get(model, identifier)
                if (
                    target is None
                    or getattr(target, "is_demo", False)
                    or (isinstance(target, AcademicProgram) and target.university.is_demo)
                ):
                    conflict("scope", scope.id, "Target is missing or demo data")
                elif (
                    isinstance(target, AcademicProgram)
                    and scope.degree_level
                    and scope.degree_level != target.degree_level
                ):
                    conflict("scope", scope.id, "Scope degree disagrees with program")
                classify(
                    "scope",
                    ScholarshipScope,
                    scope.id,
                    {**scope.model_dump(), "scholarship_id": record.id},
                    scopes.get(scope.id),
                )
            for program_id in sorted(expected_programs):
                values = {"scholarship_id": record.id, "program_id": program_id}
                classify(
                    "scholarship_program",
                    ScholarshipProgram,
                    record.id + ":" + program_id,
                    values,
                    session.get(ScholarshipProgram, (record.id, program_id)),
                )
        values_list = [evidence_values(e) for e in batch.evidence]
        evidence = list(
            session.scalars(
                select(VerificationRecord).where(
                    or_(
                        VerificationRecord.id.in_([v["id"] for v in values_list]),
                        VerificationRecord.scholarship_id.in_([r.id for r in batch.scholarships])
                        & VerificationRecord.source_id.in_([s.id for s in batch.sources]),
                    )
                )
            )
        )
        by_id = {r.id: r for r in evidence}
        pairs = {(r.scholarship_id, r.source_id): r for r in evidence if r.review_field is None}
        for values in values_list:
            pair = pairs.get((values["scholarship_id"], values["source_id"]))
            existing = by_id.get(values["id"])
            if (pair is not None and pair.id != values["id"]) or (
                existing is not None and existing.review_field is not None
            ):
                conflict("evidence", values["id"], "Existing attribution identity differs")
            else:
                classify("evidence", VerificationRecord, values["id"], values, existing)
    return plan


def apply_scholarship_import(session, batch):
    with session.begin_nested():
        plan = preview_scholarship_import(session, batch)
        if plan.conflicts:
            raise ImportConflict(plan)
        for model in (DataSource, Scholarship, ScholarshipProgram, VerificationRecord):
            for row_model, values in plan.rows:
                if row_model is not model:
                    continue
                if model is Scholarship:
                    # Parent state and scopes must enter the ORM flush atomically.
                    values = {
                        **values,
                        "scopes": [
                            ScholarshipScope(**s)
                            for m, s in plan.rows
                            if m is ScholarshipScope and s["scholarship_id"] == values["id"]
                        ],
                    }
                elif model is VerificationRecord:
                    values = {
                        **values,
                        "verification_status": "unverified",
                        "reviewed_fields": "",
                        "reviewed_at": None,
                        "reviewed_by": None,
                        "valid_from": None,
                        "valid_until": None,
                    }
                session.add(model(**values))
            session.flush()
    return plan
