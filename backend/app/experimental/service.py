"""Owner-only synthetic services. Router/test gate is mandatory; no operational calls."""

from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.experimental import models as m
from app.experimental import schemas as s
from app.models.catalog import AcademicProgram, University
from app.models.student import User
from app.services.security import now


def lock_owner(db, user):
    owner = db.scalar(select(User).where(User.id == user.id).with_for_update())
    if owner is None or owner.account_status != "active":
        raise HTTPException(401, "Sign in to continue.")


def page_meta(page, size, total):
    return {"page": page, "page_size": size, "total": total, "pages": (total + size - 1) // size}


def saved_dto(db, row):
    program = db.get(AcademicProgram, row.program_id)
    available = program is not None and program.university.status == "active"
    return {
        "id": row.program_id,
        "created_at": row.created_at,
        "availability": "available" if available else "unavailable",
        "program": {"id": program.id, "name": program.name} if available else None,
    }


def saved_list(db, user, page, size):
    query = select(m.SavedProgram).where(m.SavedProgram.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    return {"items": saved_items(db, user, page, size), "meta": page_meta(page, size, total)}


def saved_items(db, user, page=1, size=None):
    query = (
        select(
            m.SavedProgram.program_id,
            m.SavedProgram.created_at,
            AcademicProgram.name,
            University.status,
        )
        .outerjoin(AcademicProgram, AcademicProgram.id == m.SavedProgram.program_id)
        .outerjoin(University, University.id == AcademicProgram.university_id)
        .where(m.SavedProgram.user_id == user.id)
        .order_by(m.SavedProgram.created_at, m.SavedProgram.program_id)
    )
    if size is not None:
        query = query.offset((page - 1) * size).limit(size)
    return [
        {
            "id": row.program_id,
            "created_at": row.created_at,
            "availability": "available" if row.status == "active" and row.name else "unavailable",
            "program": {"id": row.program_id, "name": row.name}
            if row.status == "active" and row.name
            else None,
        }
        for row in db.execute(query)
    ]


def save_program(db, user, identifier):
    lock_owner(db, user)
    current = db.get(m.SavedProgram, (user.id, identifier))
    if current:
        return saved_dto(db, current), False
    exists = db.scalar(
        select(AcademicProgram.id)
        .join(University)
        .where(AcademicProgram.id == identifier, University.status == "active")
    )
    if not exists:
        raise HTTPException(404, "Program unavailable.")
    if (
        db.scalar(
            select(func.count())
            .select_from(m.SavedProgram)
            .where(m.SavedProgram.user_id == user.id)
        )
        >= 500
    ):
        raise HTTPException(409, "Saved-program limit reached.")
    db.execute(
        insert(m.saved).values(user_id=user.id, program_id=identifier).on_conflict_do_nothing()
    )
    return saved_dto(db, db.get(m.SavedProgram, (user.id, identifier))), True


def remove_program(db, user, identifier):
    lock_owner(db, user)
    db.execute(
        delete(m.SavedProgram).where(
            m.SavedProgram.user_id == user.id, m.SavedProgram.program_id == identifier
        )
    )


KINDS = {
    "academic": (m.AcademicCredential, s.AcademicCreate, s.AcademicRead),
    "language": (m.LanguageCredential, s.LanguageCreate, s.LanguageRead),
}


def owned_record(db, user, kind, identifier):
    model = KINDS[kind][0]
    row = db.scalar(select(model).where(model.id == identifier, model.user_id == user.id))
    if row is None:
        raise HTTPException(404, "Credential not found.")
    return row


def credential_dto(db, kind, row):
    create, read = KINDS[kind][1:]
    values = {key: getattr(row, key) for key in create.model_fields if key != "components"}
    if kind == "language":
        values["components"] = [
            {"component": c.component, "score": c.score, "score_scale": c.score_scale}
            for c in db.scalars(
                select(m.LanguageComponent)
                .where(m.LanguageComponent.credential_id == row.id)
                .order_by(m.LanguageComponent.component)
            )
        ]
    values.update(
        {
            key: getattr(row, key)
            for key in ("id", "version", "evidence_status", "created_at", "updated_at")
        }
    )
    return read.model_validate(values)


def credential_list(db, user, kind, page, size):
    model = KINDS[kind][0]
    query = select(model).where(model.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    return {
        "items": [
            credential_dto(db, kind, row)
            for row in db.scalars(
                query.order_by(model.created_at, model.id).offset((page - 1) * size).limit(size)
            )
        ],
        "meta": page_meta(page, size, total),
    }


def replace_components(db, identifier, components):
    db.execute(delete(m.LanguageComponent).where(m.LanguageComponent.credential_id == identifier))
    for component in components:
        db.add(m.LanguageComponent(credential_id=identifier, **component.model_dump()))


def create_credential(db, user, kind, data):
    lock_owner(db, user)
    model = KINDS[kind][0]
    if db.scalar(select(func.count()).select_from(model).where(model.user_id == user.id)) >= 50:
        raise HTTPException(409, "Credential limit reached.")
    row = model(id=uuid4(), user_id=user.id, **data.model_dump(exclude={"components"}))
    db.add(row)
    db.flush()
    if kind == "language":
        replace_components(db, row.id, data.components)
        db.flush()
    return credential_dto(db, kind, row)


def update_credential(db, user, kind, identifier, patch):
    lock_owner(db, user)
    row = owned_record(db, user, kind, identifier)
    if row.version != patch.expected_version:
        raise HTTPException(409, "Credential changed; refresh before editing.")
    values = credential_dto(db, kind, row).model_dump(include=KINDS[kind][1].model_fields.keys())
    values.update(patch.model_dump(exclude={"expected_version"}, exclude_unset=True))
    try:
        data = KINDS[kind][1].model_validate(values)
    except ValidationError:
        raise HTTPException(422, "Invalid credential field combination.") from None
    for key, value in data.model_dump(exclude={"components"}).items():
        setattr(row, key, value)
    row.version += 1
    row.updated_at = now()
    if kind == "language":
        replace_components(db, row.id, data.components)
    db.flush()
    return credential_dto(db, kind, row)


def remove_credential(db, user, kind, identifier):
    lock_owner(db, user)
    model = KINDS[kind][0]
    db.execute(delete(model).where(model.id == identifier, model.user_id == user.id))


CHOICES = {
    "countries": "country",
    "degrees": "degree",
    "interests": "interest",
    "teaching_languages": "language",
}


def read_preferences(db, user):
    row = db.get(m.StudyPreferences, user.id)
    result = {key: [] for key in CHOICES}
    result.update(
        {
            "version": row.version if row else 0,
            "updated_at": row.updated_at if row else None,
            "budget": None,
            "intake_window": None,
        }
    )
    if row:
        for choice in db.scalars(
            select(m.PreferenceChoice)
            .where(m.PreferenceChoice.user_id == user.id)
            .order_by(m.PreferenceChoice.kind, m.PreferenceChoice.value)
        ):
            key = next(key for key, kind in CHOICES.items() if kind == choice.kind)
            result[key].append(choice.value)
        if row.budget_amount is not None:
            result["budget"] = {
                "amount": format(row.budget_amount, ".2f"),
                "currency": row.budget_currency,
                "period": row.budget_period,
            }
        if row.intake_from is not None or row.intake_until is not None:
            result["intake_window"] = {"start": row.intake_from, "end": row.intake_until}
    return result


def replace_preferences(db, user, data):
    lock_owner(db, user)
    row = db.get(m.StudyPreferences, user.id)
    if data.expected_version != (row.version if row else 0):
        raise HTTPException(409, "Preferences changed; refresh before editing.")
    if row is None:
        row = m.StudyPreferences(user_id=user.id, version=1)
        db.add(row)
    else:
        row.version += 1
    row.updated_at = now()
    row.budget_amount = data.budget.amount if data.budget else None
    row.budget_currency = data.budget.currency if data.budget else None
    row.budget_period = data.budget.period if data.budget else None
    row.intake_from = data.intake_window.start if data.intake_window else None
    row.intake_until = data.intake_window.end if data.intake_window else None
    db.flush()
    db.execute(delete(m.PreferenceChoice).where(m.PreferenceChoice.user_id == user.id))
    for key, kind in CHOICES.items():
        for value in getattr(data, key):
            db.add(m.PreferenceChoice(user_id=user.id, kind=kind, value=value))
    db.flush()
    return read_preferences(db, user)


def remove_preferences(db, user):
    lock_owner(db, user)
    db.execute(delete(m.StudyPreferences).where(m.StudyPreferences.user_id == user.id))


def export_foundation(db, user):
    result = {
        "saved_programs": saved_items(db, user),
        "study_preferences": read_preferences(db, user),
    }
    for kind, (model, _, _) in KINDS.items():
        result[kind + "_credentials"] = [
            credential_dto(db, kind, row)
            for row in db.scalars(
                select(model).where(model.user_id == user.id).order_by(model.created_at, model.id)
            )
        ]
    return result
