"""Private personal workflow; no official admissions inference or external sending."""

from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.experimental.service import lock_owner
from app.journey import models as m
from app.journey import schemas as s
from app.models.catalog import AcademicProgram, University
from app.services.security import now


def paginate(db, query, page, size, encode):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(query.offset((page - 1) * size).limit(size))
    return {
        "items": [encode(r) for r in rows],
        "meta": {
            "page": page,
            "page_size": size,
            "total": total,
            "pages": (total + size - 1) // size,
        },
    }


def owned(db, user, identifier):
    row = db.scalar(
        select(m.StudentApplication).where(
            m.StudentApplication.id == identifier, m.StudentApplication.user_id == user.id
        )
    )
    if row is None:
        raise HTTPException(404, "Application not found.")
    return row


def check_version(row, expected):
    if row.version != expected:
        raise HTTPException(409, "Record changed; refresh before editing.")


def application_dto(db, row):
    university = db.get(University, row.university_id)
    return s.ApplicationRead.model_validate(
        {
            **{key: getattr(row, key) for key in s.ApplicationCreate.model_fields},
            **{
                key: getattr(row, key)
                for key in ("id", "stage", "archived", "version", "created_at", "updated_at")
            },
            "link_available": university is not None and university.status == "active",
        }
    )


def validate_links(db, data):
    university = db.get(University, data.university_id)
    if university is None or university.status != "active":
        raise HTTPException(404, "University unavailable.")
    if data.program_id is not None:
        program = db.get(AcademicProgram, data.program_id)
        if program is None or program.university_id != data.university_id:
            raise HTTPException(422, "Program must belong to the selected existing university.")


def safe_flush(db):
    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(
            409, "A matching application or concurrent record already exists."
        ) from None


def create(db, user, data):
    lock_owner(db, user)
    validate_links(db, data)
    if (
        db.scalar(
            select(func.count())
            .select_from(m.StudentApplication)
            .where(m.StudentApplication.user_id == user.id)
        )
        >= 100
    ):
        raise HTTPException(409, "Personal application limit reached.")
    row = m.StudentApplication(id=uuid4(), user_id=user.id, **data.model_dump())
    db.add(row)
    safe_flush(db)
    return application_dto(db, row)


def list_applications(db, user, page, size, archived=False, stage=None):
    query = select(m.StudentApplication).where(
        m.StudentApplication.user_id == user.id, m.StudentApplication.archived == archived
    )
    if stage is not None:
        query = query.where(m.StudentApplication.stage == stage)
    return paginate(
        db,
        query.order_by(m.StudentApplication.created_at, m.StudentApplication.id),
        page,
        size,
        lambda row: application_dto(db, row),
    )


def update(db, user, identifier, patch):
    lock_owner(db, user)
    row = owned(db, user, identifier)
    check_version(row, patch.expected_version)
    values = {key: getattr(row, key) for key in s.ApplicationCreate.model_fields}
    change = patch.model_dump(exclude_unset=True, exclude={"expected_version", "archived"})
    values.update(change)
    try:
        data = s.ApplicationCreate.model_validate(values)
    except ValidationError:
        raise HTTPException(422, "Invalid application fields.") from None
    if "university_id" in change or "program_id" in change:
        validate_links(db, data)
    if "archived" in patch.model_fields_set and patch.archived is None:
        raise HTTPException(422, "Archive state cannot be null.")
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    if "archived" in patch.model_fields_set:
        row.archived = patch.archived
    row.version += 1
    row.updated_at = now()
    row.stage_change_reason = None
    safe_flush(db)
    return application_dto(db, row)


def change_stage(db, user, identifier, data):
    lock_owner(db, user)
    row = owned(db, user, identifier)
    check_version(row, data.expected_version)
    if row.stage == data.stage:
        return application_dto(db, row)
    if row.stage in {"ENROLLED", "REJECTED", "WITHDRAWN"} and not data.reason:
        raise HTTPException(
            422, "Reopening/correcting a terminal personal stage requires a reason."
        )
    row.stage = data.stage
    row.stage_change_reason = data.reason
    row.version += 1
    row.updated_at = now()
    db.flush()
    return application_dto(db, row)


def remove(db, user, identifier, data):
    lock_owner(db, user)
    row = owned(db, user, identifier)
    check_version(row, data.expected_version)
    db.delete(row)
    db.flush()


def timeline(db, user, identifier, page, size):
    owned(db, user, identifier)
    query = (
        select(m.ApplicationStatusEvent)
        .where(
            m.ApplicationStatusEvent.user_id == user.id,
            m.ApplicationStatusEvent.application_id == identifier,
        )
        .order_by(m.ApplicationStatusEvent.version.desc())
    )
    return paginate(db, query, page, size, s.EventRead.model_validate)


def item_owned(db, user, application_id, item_id):
    owned(db, user, application_id)
    row = db.scalar(
        select(m.ApplicationItem).where(
            m.ApplicationItem.id == item_id,
            m.ApplicationItem.application_id == application_id,
            m.ApplicationItem.user_id == user.id,
        )
    )
    if row is None:
        raise HTTPException(404, "Planning item not found.")
    return row


def validate_timezone(db, data, check_offset=True):
    if data.timezone is None:
        return
    if not db.scalar(
        text("SELECT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=:zone)"),
        {"zone": data.timezone},
    ):
        raise HTTPException(422, "Choose an existing IANA timezone or UTC.")
    if data.reminder_at is not None and check_offset:
        local = db.scalar(
            text("SELECT CAST(:instant AS timestamptz) AT TIME ZONE :zone"),
            {"instant": data.reminder_at, "zone": data.timezone},
        )
        if local != data.reminder_at.replace(tzinfo=None):
            raise HTTPException(
                422,
                "The explicit time offset must match the selected timezone, including daylight saving.",
            )


def add_item(db, user, application_id, data):
    lock_owner(db, user)
    owned(db, user, application_id)
    validate_timezone(db, data)
    if (
        db.scalar(
            select(func.count())
            .select_from(m.ApplicationItem)
            .where(m.ApplicationItem.application_id == application_id)
        )
        >= 100
    ):
        raise HTTPException(409, "Application planning item limit reached.")
    row = m.ApplicationItem(
        id=uuid4(), application_id=application_id, user_id=user.id, **data.model_dump()
    )
    db.add(row)
    db.flush()
    return s.ItemRead.model_validate(row)


def update_item(db, user, application_id, item_id, patch):
    lock_owner(db, user)
    row = item_owned(db, user, application_id, item_id)
    check_version(row, patch.expected_version)
    values = {key: getattr(row, key) for key in s.ItemCreate.model_fields}
    values.update(patch.model_dump(exclude_unset=True, exclude={"expected_version"}))
    try:
        data = s.ItemCreate.model_validate(values)
    except ValidationError:
        raise HTTPException(422, "Invalid planning item fields.") from None
    changed_zone = "timezone" in patch.model_fields_set and patch.timezone != row.timezone
    if data.reminder_at and changed_zone and "reminder_at" not in patch.model_fields_set:
        raise HTTPException(
            422, "Changing an instant reminder timezone requires its explicit offset time again."
        )
    validate_timezone(db, data, check_offset="reminder_at" in patch.model_fields_set)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    row.version += 1
    row.updated_at = now()
    db.flush()
    return s.ItemRead.model_validate(row)


def list_items(db, user, application_id, page, size, kind=None, completed=None, due_before=None):
    owned(db, user, application_id)
    query = select(m.ApplicationItem).where(
        m.ApplicationItem.user_id == user.id, m.ApplicationItem.application_id == application_id
    )
    if kind:
        query = query.where(m.ApplicationItem.kind == kind)
    if completed is not None:
        query = query.where(m.ApplicationItem.completed == completed)
    if due_before:
        query = query.where(m.ApplicationItem.due_date <= due_before)
    return paginate(
        db,
        query.order_by(m.ApplicationItem.created_at, m.ApplicationItem.id),
        page,
        size,
        s.ItemRead.model_validate,
    )


def remove_item(db, user, application_id, item_id, expected_version):
    lock_owner(db, user)
    row = item_owned(db, user, application_id, item_id)
    check_version(row, expected_version)
    db.delete(row)
    db.flush()


def dashboard(db, user):
    applications = list(
        db.scalars(select(m.StudentApplication).where(m.StudentApplication.user_id == user.id))
    )
    active = [a for a in applications if not a.archived]
    ids = {a.id for a in active}
    items = list(db.scalars(select(m.ApplicationItem).where(m.ApplicationItem.user_id == user.id)))
    items = [i for i in items if i.application_id in ids]
    tasks = [i for i in items if i.kind == "task"]
    instant = now()
    zones = sorted({i.timezone for i in items if i.timezone})
    dates = (
        dict(
            db.execute(
                text(
                    "SELECT zone,(CAST(:instant AS timestamptz) AT TIME ZONE zone)::date FROM unnest(CAST(:zones AS text[])) AS zone"
                ),
                {"instant": instant, "zones": zones},
            ).all()
        )
        if zones
        else {}
    )
    overdue = sum(
        not i.completed and i.due_date is not None and i.due_date < dates[i.timezone] for i in tasks
    )
    upcoming = [
        i
        for i in items
        if i.kind == "reminder"
        and not i.completed
        and (
            i.reminder_mode == "instant"
            and i.reminder_at >= instant
            or i.reminder_mode == "date"
            and i.reminder_date >= dates[i.timezone]
        )
    ]
    upcoming.sort(key=lambda i: (i.reminder_date or i.reminder_at.date(), str(i.id)))
    recent = list(
        db.scalars(
            select(m.ApplicationStatusEvent)
            .where(m.ApplicationStatusEvent.user_id == user.id)
            .order_by(m.ApplicationStatusEvent.changed_at.desc(), m.ApplicationStatusEvent.id)
            .limit(10)
        )
    )
    return {
        "total_applications": len(active),
        "archived_applications": len(applications) - len(active),
        "by_stage": {stage: sum(a.stage == stage for a in active) for stage in m.STAGES},
        "pending_personal_tasks": sum(not i.completed for i in tasks),
        "completed_personal_tasks": sum(bool(i.completed) for i in tasks),
        "overdue_personal_tasks": overdue,
        "upcoming_personal_reminders": [s.ItemRead.model_validate(i) for i in upcoming[:10]],
        "recent_personal_events": [s.EventRead.model_validate(e) for e in recent],
        "missing_cycle": sum(a.cycle_key is None for a in active),
        "missing_program": sum(a.program_id is None for a in active),
        "explanation": "Personal stored-record progress only. Stages, documents and task completion do not establish submission, receipt, acceptance or admission. Official requirements/deadlines are UNKNOWN. Reminders are displayed here only; none are sent.",
    }


def export(db, user):
    return {
        "applications": [
            application_dto(db, a)
            for a in db.scalars(
                select(m.StudentApplication)
                .where(m.StudentApplication.user_id == user.id)
                .order_by(m.StudentApplication.created_at, m.StudentApplication.id)
            )
        ],
        "status_events": [
            s.EventRead.model_validate(e)
            for e in db.scalars(
                select(m.ApplicationStatusEvent)
                .where(m.ApplicationStatusEvent.user_id == user.id)
                .order_by(m.ApplicationStatusEvent.changed_at, m.ApplicationStatusEvent.id)
            )
        ],
        "items": [
            s.ItemRead.model_validate(i)
            for i in db.scalars(
                select(m.ApplicationItem)
                .where(m.ApplicationItem.user_id == user.id)
                .order_by(m.ApplicationItem.created_at, m.ApplicationItem.id)
            )
        ],
    }
