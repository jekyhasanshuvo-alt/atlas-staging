"""Create-only catalog import. The operator owns the outer database transaction."""

import hashlib
import json
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.catalog import (
    AcademicProgram,
    City,
    Country,
    DataSource,
    University,
    VerificationRecord,
)
from app.schemas.curated import CuratedBatch


@dataclass
class ImportPlan:
    created: list[dict] = field(default_factory=list)
    unchanged: list[dict] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    rows: list[tuple[type, dict]] = field(default_factory=list, repr=False)

    def report(self, applied=False):
        return {
            "applied": applied,
            "created" if applied else "would_create": self.created,
            "unchanged": self.unchanged,
            "conflicts": self.conflicts,
            "counts": {
                "created" if applied else "would_create": len(self.created),
                "unchanged": len(self.unchanged),
                "conflicting": len(self.conflicts),
            },
        }


class ImportConflict(ValueError):
    def __init__(self, plan):
        super().__init__("Import conflicts; no changes applied")
        self.plan = plan


def evidence_values(evidence):
    identity = f"{evidence.entity_type}:{evidence.entity_id}:{evidence.source_id}"
    return {
        "id": "curated-" + hashlib.sha256(identity.encode()).hexdigest(),
        "university_id": evidence.entity_id if evidence.entity_type == "university" else None,
        "program_id": evidence.entity_id if evidence.entity_type == "program" else None,
        "scholarship_id": evidence.entity_id if evidence.entity_type == "scholarship" else None,
        "living_estimate_id": None,
        "source_id": evidence.source_id,
        # Attribute curator claims without pretending that a review has occurred.
        "notes": json.dumps(
            {
                "schema_version": 1,
                "attributed_fields": evidence.fields,
                "curator_notes": evidence.notes,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    }


def preview_import(session: Session, batch: CuratedBatch) -> ImportPlan:
    if batch.schema_version == 2:
        from app.services.scholarship_import import preview_scholarship_import

        return preview_scholarship_import(session, batch)
    plan = ImportPlan()
    with session.no_autoflush:
        universities = {
            u.id: u
            for u in session.scalars(
                select(University).where(
                    University.id.in_(
                        {u.id for u in batch.universities}
                        | {p.university_id for p in batch.programs}
                    )
                )
            )
        }
        slugs = {
            u.slug: u.id
            for u in session.scalars(
                select(University).where(University.slug.in_([u.slug for u in batch.universities]))
            )
        }
        programs = {
            p.id: p
            for p in session.scalars(
                select(AcademicProgram).where(
                    AcademicProgram.id.in_([p.id for p in batch.programs])
                )
            )
        }
        sources = {
            s.id: s
            for s in session.scalars(
                select(DataSource).where(DataSource.id.in_([s.id for s in batch.sources]))
            )
        }
        cities = {
            c.id: c
            for c in session.scalars(
                select(City).where(City.id.in_([u.city_id for u in batch.universities]))
            )
        }
        countries = set(
            session.scalars(
                select(Country.id).where(Country.id.in_([u.country_id for u in batch.universities]))
            )
        )
        evidence_rows = [evidence_values(e) for e in batch.evidence]
        existing_evidence = list(
            session.scalars(
                select(VerificationRecord).where(
                    or_(
                        VerificationRecord.id.in_([e["id"] for e in evidence_rows]),
                        (
                            VerificationRecord.source_id.in_(sources.keys())
                            & (
                                VerificationRecord.university_id.in_(
                                    [u.id for u in batch.universities]
                                )
                                | VerificationRecord.program_id.in_([p.id for p in batch.programs])
                            )
                        ),
                    )
                )
            )
        )

        def conflict(kind, identifier, reason):
            plan.conflicts.append({"entity": kind, "id": identifier, "reason": reason})

        def classify(kind, model, values, existing):
            identifier = values["id"]
            if existing is not None:
                if getattr(existing, "is_demo", False) or (
                    model is DataSource and existing.source_type == "demo"
                ):
                    conflict(
                        kind, identifier, "Existing demo record cannot be imported or overwritten"
                    )
                elif any(getattr(existing, key) != value for key, value in values.items()):
                    conflict(kind, identifier, "Existing content differs")
                else:
                    plan.unchanged.append({"entity": kind, "id": identifier})
            else:
                plan.created.append({"entity": kind, "id": identifier})
                plan.rows.append((model, values))

        for source in batch.sources:
            classify("source", DataSource, source.model_dump(), sources.get(source.id))
        for university in batch.universities:
            if (
                university.country_id not in countries
                or university.city_id not in cities
                or cities[university.city_id].country_id != university.country_id
            ):
                conflict(
                    "university",
                    university.id,
                    "Country/city is missing or belongs to a different country",
                )
                continue
            if university.slug in slugs and slugs[university.slug] != university.id:
                conflict("university", university.id, "Slug belongs to another university")
                continue
            classify(
                "university",
                University,
                {**university.model_dump(), "is_demo": False, "status": "active"},
                universities.get(university.id),
            )
        batch_universities = {u.id for u in batch.universities}
        for program in batch.programs:
            parent = universities.get(program.university_id)
            if (program.university_id not in batch_universities and parent is None) or (
                parent is not None and parent.is_demo
            ):
                conflict("program", program.id, "Parent university is missing or is demo data")
                continue
            classify(
                "program",
                AcademicProgram,
                {**program.model_dump(), "is_demo": False},
                programs.get(program.id),
            )
        by_id = {r.id: r for r in existing_evidence if r.review_field is None}
        by_pair = {
            (r.source_id, r.university_id, r.program_id): r
            for r in existing_evidence
            if r.review_field is None
        }
        for values in evidence_rows:
            pair = by_pair.get((values["source_id"], values["university_id"], values["program_id"]))
            if pair is not None and pair.id != values["id"]:
                conflict(
                    "evidence", values["id"], "Source/target evidence already has a different ID"
                )
                continue
            classify("evidence", VerificationRecord, values, by_id.get(values["id"]))
    return plan


def apply_import(session: Session, batch: CuratedBatch, *, confirmed: bool = False) -> ImportPlan:
    if not confirmed:
        raise ValueError("Apply requires explicit confirmation")
    if session.new or session.dirty or session.deleted:
        raise ValueError("Use a clean session dedicated to the import")
    if batch.schema_version == 2:
        from app.services.scholarship_import import apply_scholarship_import

        return apply_scholarship_import(session, batch)
    # Savepoint also protects callers that catch an error inside their own transaction.
    # The CLI commits the complete batch only after this function succeeds.
    with session.begin_nested():
        plan = preview_import(session, batch)
        if plan.conflicts:
            raise ImportConflict(plan)
        for model in (DataSource, University, AcademicProgram, VerificationRecord):
            for row_model, values in plan.rows:
                if row_model is model:
                    if model is VerificationRecord:
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
