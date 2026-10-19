"""Independent proposed0006 metadata, never registered with active Alembic Base."""

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    Uuid,
    text,
)
from sqlalchemy import CheckConstraint as Check
from sqlalchemy import Column as C
from sqlalchemy import ForeignKey as FK
from sqlalchemy import UniqueConstraint as Unique
from sqlalchemy.orm import registry

from app.experimental.models import metadata as foundation_metadata

metadata = MetaData()
for table in foundation_metadata.sorted_tables:
    table.to_metadata(metadata)
Unique(
    metadata.tables["academic_programs"].c.id,
    metadata.tables["academic_programs"].c.university_id,
    name="uq_academic_programs_journey_scope",
)
mapper_registry = registry(metadata=metadata)
STAGES = (
    "RESEARCHING",
    "SHORTLISTED",
    "PREPARING",
    "READY_TO_SUBMIT",
    "SUBMITTED",
    "UNDER_REVIEW",
    "OFFER_RECEIVED",
    "REJECTED",
    "WITHDRAWN",
    "ENROLLED",
)
stage_sql = ",".join(repr(s) for s in STAGES)


def identity():
    return C("id", Uuid, primary_key=True)


def version():
    return C("version", Integer, nullable=False, server_default="1")


def timestamp(name):
    return C(name, DateTime(timezone=True), nullable=False, server_default=text("now()"))


applications = Table(
    "student_applications",
    metadata,
    identity(),
    C("user_id", Uuid, FK("users.id", ondelete="CASCADE"), nullable=False),
    C("university_id", String(36), FK("universities.id", ondelete="RESTRICT"), nullable=False),
    C("program_id", String(36)),
    C("label", String(160), nullable=False),
    C("cycle_key", String(80)),
    C("route_key", String(80)),
    C("stage", String(30), nullable=False, server_default="RESEARCHING"),
    C("stage_change_reason", String(500)),
    C("archived", Boolean, nullable=False, server_default=text("false")),
    version(),
    timestamp("created_at"),
    timestamp("updated_at"),
    ForeignKeyConstraint(
        ["program_id", "university_id"],
        ["academic_programs.id", "academic_programs.university_id"],
        ondelete="RESTRICT",
    ),
    Unique("id", "user_id"),
    Unique(
        "user_id",
        "university_id",
        "program_id",
        "cycle_key",
        "route_key",
        postgresql_nulls_not_distinct=True,
    ),
    Check("length(trim(label)) > 0"),
    Check("length(trim(cycle_key)) > 0"),
    Check("length(trim(route_key)) > 0"),
    Check(f"stage IN ({stage_sql})"),
    Check("stage_change_reason IS NULL OR length(trim(stage_change_reason)) > 0"),
    Check("version > 0"),
)
Index(
    "ix_applications_owner_created",
    applications.c.user_id,
    applications.c.created_at,
    applications.c.id,
)
Index("ix_applications_university", applications.c.university_id)
Index("ix_applications_program_scope", applications.c.program_id, applications.c.university_id)
events = Table(
    "application_status_events",
    metadata,
    identity(),
    C("application_id", Uuid, nullable=False),
    C("user_id", Uuid, nullable=False),
    C("previous_stage", String(30)),
    C("new_stage", String(30), nullable=False),
    C("version", Integer, nullable=False),
    C("changed_at", DateTime(timezone=True), nullable=False),
    C("reason", String(500)),
    ForeignKeyConstraint(
        ["application_id", "user_id"],
        ["student_applications.id", "student_applications.user_id"],
        ondelete="CASCADE",
    ),
    Unique("application_id", "version"),
    Check(f"previous_stage IS NULL OR previous_stage IN ({stage_sql})"),
    Check(f"new_stage IN ({stage_sql})"),
    Check("version > 0"),
    Check("reason IS NULL OR length(trim(reason)) > 0"),
)
Index("ix_application_events_owner_time", events.c.user_id, events.c.changed_at, events.c.id)
items = Table(
    "application_items",
    metadata,
    identity(),
    C("application_id", Uuid, nullable=False),
    C("user_id", Uuid, nullable=False),
    C("kind", String(20), nullable=False),
    C("title", String(160), nullable=False),
    C("description", Text),
    C("completed", Boolean),
    C("priority", String(10)),
    C("document_state", String(20)),
    C("due_date", Date),
    C("reminder_mode", String(10)),
    C("reminder_date", Date),
    C("reminder_at", DateTime(timezone=True)),
    C("timezone", String(80)),
    version(),
    timestamp("created_at"),
    timestamp("updated_at"),
    ForeignKeyConstraint(
        ["application_id", "user_id"],
        ["student_applications.id", "student_applications.user_id"],
        ondelete="CASCADE",
    ),
    Check("kind IN ('task','document','reminder','note')"),
    Check("length(trim(title)) > 0"),
    Check("description IS NULL OR length(description) BETWEEN 1 AND 2000"),
    Check("priority IN ('low','normal','high')"),
    Check("document_state IN ('NOT_STARTED','IN_PROGRESS','READY','SUBMITTED','NOT_APPLICABLE')"),
    Check("reminder_mode IN ('date','instant')"),
    Check("version > 0"),
    Check("""(kind='task' AND completed IS NOT NULL AND priority IS NOT NULL AND document_state IS NULL
      AND reminder_mode IS NULL AND reminder_date IS NULL AND reminder_at IS NULL
      AND ((due_date IS NULL AND timezone IS NULL) OR (due_date IS NOT NULL AND timezone IS NOT NULL))) OR
      (kind='document' AND document_state IS NOT NULL AND completed IS NULL AND priority IS NULL
      AND num_nonnulls(due_date,reminder_mode,reminder_date,reminder_at,timezone)=0) OR
      (kind='reminder' AND completed IS NOT NULL AND priority IS NULL AND document_state IS NULL
      AND due_date IS NULL AND timezone IS NOT NULL AND reminder_mode IS NOT NULL AND
      ((reminder_mode='date' AND reminder_date IS NOT NULL AND reminder_at IS NULL) OR
       (reminder_mode='instant' AND reminder_at IS NOT NULL AND reminder_date IS NULL))) OR
      (kind='note' AND completed IS NULL AND priority IS NULL AND document_state IS NULL
      AND num_nonnulls(due_date,reminder_mode,reminder_date,reminder_at,timezone)=0)"""),
)
Index(
    "ix_application_items_owner_kind", items.c.user_id, items.c.kind, items.c.created_at, items.c.id
)
Index("ix_application_items_parent", items.c.application_id, items.c.user_id)


@mapper_registry.mapped
class StudentApplication:
    __table__ = applications


@mapper_registry.mapped
class ApplicationStatusEvent:
    __table__ = events


@mapper_registry.mapped
class ApplicationItem:
    __table__ = items
