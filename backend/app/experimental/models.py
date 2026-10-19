"""0005 ORM in a separate registry; importing this never extends active Base.metadata."""

from sqlalchemy import (
    CheckConstraint as Check,
)
from sqlalchemy import (
    Column as C,
)
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    Uuid,
    text,
)
from sqlalchemy import (
    ForeignKey as FK,
)
from sqlalchemy import (
    UniqueConstraint as Unique,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import registry

from app.db.base import Base
from app.models import catalog, student  # noqa: F401

metadata = MetaData()
for original in Base.metadata.sorted_tables:
    original.to_metadata(metadata)
mapper_registry = registry(metadata=metadata)


def owner(primary=False, target="users.id"):
    return C("user_id", Uuid, FK(target, ondelete="CASCADE"), primary_key=primary, nullable=False)


def timestamp(name="created_at"):
    return C(name, DateTime(timezone=True), nullable=False, server_default=text("now()"))


def identity():
    return C("id", Uuid, primary_key=True)


def version():
    return C("version", Integer, nullable=False, server_default="1")


def report_state():
    return C("evidence_status", String(20), nullable=False, server_default="self_reported")


saved = Table(
    "saved_programs",
    metadata,
    owner(True),
    C("program_id", String(36), FK("academic_programs.id", ondelete="CASCADE"), primary_key=True),
    timestamp(),
)
Index("ix_saved_programs_program", saved.c.program_id)
Index("ix_saved_programs_owner_created", saved.c.user_id, saved.c.created_at, saved.c.program_id)
academic = Table(
    "student_academic_credentials",
    metadata,
    identity(),
    owner(),
    C("credential_level", String(80)),
    C("qualification_type", String(120)),
    C("institution", String(200)),
    C("country_code", String(2)),
    C("subject", String(200)),
    C("completion_status", String(20), nullable=False, server_default="unknown"),
    C("award_date", Date),
    C("grade_value", String(80)),
    C("grade_scale", String(120)),
    C("maximum_grade", Numeric(12, 4)),
    report_state(),
    version(),
    timestamp(),
    timestamp("updated_at"),
    Check("country_code ~ '^[A-Z]{2}$'"),
    Check("completion_status IN ('unknown','in_progress','completed','incomplete')"),
    Check("maximum_grade > 0 AND maximum_grade < 100000000"),
    Check("evidence_status = 'self_reported'"),
    Check("version > 0"),
    Check("award_date IS NULL OR completion_status = 'completed'"),
    Check(
        "(grade_value IS NULL AND grade_scale IS NULL AND maximum_grade IS NULL) OR (grade_value IS NOT NULL AND grade_scale IS NOT NULL)"
    ),
)
Index("ix_academic_owner", academic.c.user_id, academic.c.created_at, academic.c.id)
language = Table(
    "student_language_credentials",
    metadata,
    identity(),
    owner(),
    C("test_type", String(80)),
    C("test_version", String(80)),
    C("test_date", Date),
    C("overall_score", Numeric(10, 4)),
    C("score_scale", String(120)),
    C("expires_on", Date),
    report_state(),
    version(),
    timestamp(),
    timestamp("updated_at"),
    Check("overall_score >= 0 AND overall_score < 100000"),
    Check("evidence_status = 'self_reported'"),
    Check("version > 0"),
    Check("overall_score IS NULL OR score_scale IS NOT NULL"),
    Check("expires_on IS NULL OR (test_date IS NOT NULL AND expires_on >= test_date)"),
)
Index("ix_language_owner", language.c.user_id, language.c.created_at, language.c.id)
components = Table(
    "student_language_components",
    metadata,
    C(
        "credential_id",
        Uuid,
        FK("student_language_credentials.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    C("component", String(80), primary_key=True),
    C("score", Numeric(10, 4), nullable=False),
    C("score_scale", String(120), nullable=False),
    Check("length(trim(component)) > 0"),
    Check("score >= 0 AND score < 100000"),
    Check("length(trim(score_scale)) > 0"),
)
preferences = Table(
    "student_study_preferences",
    metadata,
    owner(True),
    version(),
    C("budget_amount", Numeric(14, 2)),
    C("budget_currency", String(3)),
    C("budget_period", String(20)),
    C("intake_from", Date),
    C("intake_until", Date),
    timestamp("updated_at"),
    Check("version > 0"),
    Check("budget_amount >= 0 AND budget_amount <= 100000000"),
    Check("budget_currency ~ '^[A-Z]{3}$'"),
    Check("budget_period IN ('month','semester','year','degree')"),
    Check("num_nonnulls(budget_amount,budget_currency,budget_period) IN (0,3)"),
    Check("intake_until IS NULL OR intake_from IS NULL OR intake_until >= intake_from"),
)
choices = Table(
    "student_preference_choices",
    metadata,
    owner(True, "student_study_preferences.user_id"),
    C("kind", String(20), primary_key=True),
    C("value", String(200), primary_key=True),
    Check("kind IN ('country','degree','interest','language')"),
    Check("length(trim(value)) > 0"),
    Check("kind != 'country' OR value ~ '^[A-Z]{2}$'"),
    Check("kind != 'degree' OR value IN ('Bachelor','Master','PhD')"),
)
intakes = Table(
    "program_intakes",
    metadata,
    identity(),
    C("program_id", String(36), FK("academic_programs.id", ondelete="RESTRICT"), nullable=False),
    C("cycle_key", String(80), nullable=False),
    C("round_key", String(80), nullable=False),
    Check("length(trim(cycle_key)) > 0"),
    Check("length(trim(round_key)) > 0"),
    Unique("program_id", "cycle_key", "round_key"),
    Unique("id", "program_id"),
)
facts = Table(
    "catalog_fact_versions",
    metadata,
    identity(),
    *[
        C(f"{kind}_id", String(36), FK(f"{table}.id", ondelete="RESTRICT"))
        for kind, table in (
            ("program", "academic_programs"),
            ("scholarship", "scholarships"),
            ("university", "universities"),
        )
    ],
    C("intake_id", Uuid),
    C("topic", String(40), nullable=False),
    C("schema_version", Integer, nullable=False),
    C("payload", JSONB, nullable=False),
    C("content_sha256", String(64), nullable=False),
    C("predecessor_id", Uuid, FK("catalog_fact_versions.id", ondelete="RESTRICT"), unique=True),
    C("reason", String(500), nullable=False),
    C("actor_ref", String(80), nullable=False),
    timestamp(),
    ForeignKeyConstraint(
        ["intake_id", "program_id"],
        ["program_intakes.id", "program_intakes.program_id"],
        ondelete="RESTRICT",
    ),
    Check("topic IN ('admissions','scholarship_terms','catalog_correction')"),
    Check("schema_version = 1"),
    Check("jsonb_typeof(payload) = 'object'"),
    Check("content_sha256 ~ '^[0-9a-f]{64}$'"),
    Check("length(trim(reason)) > 0"),
    Check("length(trim(actor_ref)) > 0"),
    Check("num_nonnulls(program_id,scholarship_id,university_id) = 1"),
    Check(
        "(topic = 'admissions' AND intake_id IS NOT NULL AND program_id IS NOT NULL) OR (topic = 'scholarship_terms' AND scholarship_id IS NOT NULL AND intake_id IS NULL) OR (topic = 'catalog_correction' AND intake_id IS NULL)"
    ),
    Check("predecessor_id IS NULL OR predecessor_id != id"),
)
Index(
    "uq_fact_root",
    text("coalesce(program_id,'')"),
    text("coalesce(scholarship_id,'')"),
    text("coalesce(university_id,'')"),
    text("coalesce(intake_id::text,'')"),
    facts.c.topic,
    unique=True,
    postgresql_where=text("predecessor_id IS NULL"),
)
for target in ("program", "scholarship", "university", "intake"):
    Index(f"ix_fact_{target}", facts.c[f"{target}_id"])
captures = Table(
    "official_source_captures",
    metadata,
    identity(),
    C("source_id", String(36), FK("data_sources.id", ondelete="RESTRICT"), nullable=False),
    C("metadata", JSONB, nullable=False),
    C("content_sha256", String(64), nullable=False),
    C("captured_at", DateTime(timezone=True), nullable=False),
    Unique("id", "source_id"),
    Check("jsonb_typeof(metadata) = 'object'"),
    Check("content_sha256 ~ '^[0-9a-f]{64}$'"),
)
Index("ix_capture_source", captures.c.source_id)
evidence = Table(
    "fact_field_evidence",
    metadata,
    identity(),
    C("version_id", Uuid, FK("catalog_fact_versions.id", ondelete="RESTRICT"), nullable=False),
    C("field_path", String(200), nullable=False),
    C("source_id", String(36), FK("data_sources.id", ondelete="RESTRICT"), nullable=False),
    C("capture_id", Uuid, nullable=False),
    C("locator", String(500), nullable=False),
    C("excerpt", Text, nullable=False),
    ForeignKeyConstraint(
        ["capture_id", "source_id"],
        ["official_source_captures.id", "official_source_captures.source_id"],
        ondelete="RESTRICT",
    ),
    Unique("version_id", "field_path", "capture_id"),
    Unique("id", "version_id", "source_id"),
    Check("field_path ~ '^/[^[:space:]]+$'"),
    Check("length(trim(locator)) > 0"),
    Check("length(trim(excerpt)) BETWEEN 1 AND 10000"),
)
Index("ix_evidence_source", evidence.c.source_id)
Index("ix_evidence_capture", evidence.c.capture_id)
bindings = Table(
    "fact_review_bindings",
    metadata,
    C("evidence_id", Uuid, primary_key=True),
    C("version_id", Uuid, nullable=False),
    C("source_id", String(36), nullable=False),
    C(
        "review_id",
        String(80),
        FK("verification_records.id", ondelete="RESTRICT"),
        primary_key=True,
        unique=True,
    ),
    ForeignKeyConstraint(
        ["evidence_id", "version_id", "source_id"],
        [
            "fact_field_evidence.id",
            "fact_field_evidence.version_id",
            "fact_field_evidence.source_id",
        ],
        ondelete="RESTRICT",
    ),
)
Index("ix_binding_evidence", bindings.c.evidence_id, bindings.c.version_id, bindings.c.source_id)


@mapper_registry.mapped
class SavedProgram:
    __table__ = saved


@mapper_registry.mapped
class AcademicCredential:
    __table__ = academic


@mapper_registry.mapped
class LanguageCredential:
    __table__ = language


@mapper_registry.mapped
class LanguageComponent:
    __table__ = components


@mapper_registry.mapped
class StudyPreferences:
    __table__ = preferences


@mapper_registry.mapped
class PreferenceChoice:
    __table__ = choices


@mapper_registry.mapped
class ProgramIntake:
    __table__ = intakes


@mapper_registry.mapped
class CatalogFactVersion:
    __table__ = facts


@mapper_registry.mapped
class OfficialSourceCapture:
    __table__ = captures


@mapper_registry.mapped
class FactFieldEvidence:
    __table__ = evidence


@mapper_registry.mapped
class FactReviewBinding:
    __table__ = bindings
