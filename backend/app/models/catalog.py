from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.db.base import Base, Timestamps


class Country(Timestamps, Base):
    __tablename__ = "countries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    iso_code: Mapped[str] = mapped_column(String(2), unique=True)
    currency_code: Mapped[str] = mapped_column(String(3))


class City(Timestamps, Base):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("country_id", "name"), UniqueConstraint("id", "country_id"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    country_id: Mapped[str] = mapped_column(ForeignKey("countries.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    country: Mapped[Country] = relationship()


class University(Timestamps, Base):
    __tablename__ = "universities"
    __table_args__ = (
        ForeignKeyConstraint(["city_id", "country_id"], ["cities.id", "cities.country_id"]),
        CheckConstraint("status IN ('active','inactive')", name="status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    country_id: Mapped[str] = mapped_column(ForeignKey("countries.id"), index=True)
    city_id: Mapped[str] = mapped_column(String(36), index=True)
    official_website: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    institution_type: Mapped[str] = mapped_column(String(50), default="unspecified")
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    short_name: Mapped[str] = mapped_column(String(12))
    color: Mapped[str] = mapped_column(String(20), default="blue")
    country: Mapped[Country] = relationship(foreign_keys=[country_id], overlaps="city")
    city: Mapped[City] = relationship(overlaps="country")
    programs: Mapped[list[AcademicProgram]] = relationship(
        back_populates="university", order_by="AcademicProgram.id"
    )
    verifications: Mapped[list[VerificationRecord]] = relationship(back_populates="university")


class AcademicProgram(Timestamps, Base):
    __tablename__ = "academic_programs"
    __table_args__ = (
        CheckConstraint("degree_level IN ('Bachelor','Master','PhD')", name="degree"),
        CheckConstraint(
            "tuition_amount IS NULL OR tuition_amount >= 0", name="tuition_nonnegative"
        ),
        CheckConstraint("duration_months > 0", name="duration_positive"),
        CheckConstraint(
            "tuition_period IN ('year','semester','month','degree')", name="tuition_period"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    university_id: Mapped[str] = mapped_column(ForeignKey("universities.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    degree_level: Mapped[str] = mapped_column(String(20), index=True)
    field_of_study: Mapped[str] = mapped_column(String(120), index=True)
    language_of_instruction: Mapped[str] = mapped_column(String(120))
    duration_months: Mapped[int]
    tuition_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), index=True)
    tuition_currency: Mapped[str] = mapped_column(String(3), index=True)
    tuition_period: Mapped[str] = mapped_column(String(20), default="year")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    university: Mapped[University] = relationship(back_populates="programs")
    scholarship_links: Mapped[list[ScholarshipProgram]] = relationship(back_populates="program")
    verifications: Mapped[list[VerificationRecord]] = relationship(back_populates="program")


class Scholarship(Timestamps, Base):
    __tablename__ = "scholarships"
    __table_args__ = (
        CheckConstraint("funding_type IN ('Full','Partial')", name="funding_type"),
        CheckConstraint(
            "funding_amount IS NULL OR funding_amount >= 0", name="funding_nonnegative"
        ),
        CheckConstraint(
            "contract_version IN (1,2) AND (contract_version != 1 OR funding_type IS NOT NULL)",
            name="contract_version",
        ),
        CheckConstraint(
            "cycle_state IS NULL OR cycle_state IN ('known','unknown')", name="cycle_state"
        ),
        CheckConstraint(
            "applicability_state IS NULL OR applicability_state IN ('unknown','listed','unrestricted')",
            name="applicability_state",
        ),
        CheckConstraint(
            "provider_kind IS NULL OR provider_kind IN ('government','university','foundation','other','unknown')",
            name="provider_kind",
        ),
        CheckConstraint(
            "contract_version != 2 OR (scheme_key IS NOT NULL AND round_key IS NOT NULL AND cycle_state IS NOT NULL AND applicability_state IS NOT NULL)",
            name="structured_identity",
        ),
        *[
            CheckConstraint(
                f"{key} IS NULL OR jsonb_typeof({key}) = 'object'", name=f"{key}_object"
            )
            for key in ("benefits", "requirements", "deadlines")
        ],
        UniqueConstraint("scheme_key", "round_key"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    provider: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    funding_type: Mapped[str | None] = mapped_column(String(20), index=True)
    funding_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    funding_currency: Mapped[str | None] = mapped_column(String(3))
    eligibility_summary: Mapped[str] = mapped_column(Text)
    application_deadline: Mapped[date | None] = mapped_column(Date)
    official_url: Mapped[str | None] = mapped_column(Text)
    coverage: Mapped[str] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    contract_version: Mapped[int] = mapped_column(default=1, server_default="1")
    scheme_key: Mapped[str | None] = mapped_column(String(120), index=True)
    round_key: Mapped[str | None] = mapped_column(String(80))
    intake_label: Mapped[str | None] = mapped_column(String(120))
    academic_cycle: Mapped[str | None] = mapped_column(String(40))
    intake_start_date: Mapped[date | None] = mapped_column(Date)
    cycle_state: Mapped[str | None] = mapped_column(String(20))
    provider_kind: Mapped[str | None] = mapped_column(String(20))
    applicability_state: Mapped[str | None] = mapped_column(String(20))
    benefits: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    requirements: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    deadlines: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    scopes: Mapped[list[ScholarshipScope]] = relationship(back_populates="scholarship")
    program_links: Mapped[list[ScholarshipProgram]] = relationship(back_populates="scholarship")
    verifications: Mapped[list[VerificationRecord]] = relationship(back_populates="scholarship")


class ScholarshipProgram(Base):
    __tablename__ = "scholarship_programs"
    scholarship_id: Mapped[str] = mapped_column(
        ForeignKey("scholarships.id", ondelete="CASCADE"), primary_key=True
    )
    program_id: Mapped[str] = mapped_column(
        ForeignKey("academic_programs.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    scholarship: Mapped[Scholarship] = relationship(back_populates="program_links")
    program: Mapped[AcademicProgram] = relationship(back_populates="scholarship_links")


class ScholarshipScope(Base):
    __tablename__ = "scholarship_scopes"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(country_id, university_id, program_id) = 1", name="exactly_one_target"
        ),
        CheckConstraint(
            "degree_level IS NULL OR degree_level IN ('Bachelor','Master','PhD')", name="degree"
        ),
        CheckConstraint(
            "scope_extent IN ('exact_target','descendants') AND (program_id IS NULL OR scope_extent = 'exact_target')",
            name="scope_extent",
        ),
        *[
            Index(
                f"uq_scholarship_scope_{target}",
                "scholarship_id",
                f"{target}_id",
                func.coalesce(text("degree_level"), ""),
                "scope_extent",
                unique=True,
                postgresql_where=text(f"{target}_id IS NOT NULL"),
            )
            for target in ("country", "university", "program")
        ],
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scholarship_id: Mapped[str] = mapped_column(
        ForeignKey("scholarships.id", ondelete="RESTRICT"), index=True
    )
    country_id: Mapped[str | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), index=True
    )
    university_id: Mapped[str | None] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"), index=True
    )
    program_id: Mapped[str | None] = mapped_column(
        ForeignKey("academic_programs.id", ondelete="RESTRICT"), index=True
    )
    degree_level: Mapped[str | None] = mapped_column(String(20))
    scope_extent: Mapped[str] = mapped_column(
        String(20), default="exact_target", server_default="exact_target"
    )
    scholarship: Mapped[Scholarship] = relationship(back_populates="scopes")
    country: Mapped[Country | None] = relationship()
    university: Mapped[University | None] = relationship()
    program: Mapped[AcademicProgram | None] = relationship()


class LivingCostEstimate(Timestamps, Base):
    __tablename__ = "living_cost_estimates"
    __table_args__ = (
        UniqueConstraint("city_id", "currency"),
        CheckConstraint("monthly_amount >= 0", name="amount_nonnegative"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    verifications: Mapped[list[VerificationRecord]] = relationship(back_populates="living_estimate")


class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('demo','official','publication','other')", name="source_type"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(String(200))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VerificationRecord(Base):
    __tablename__ = "verification_records"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN university_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN program_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN scholarship_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN living_estimate_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="exactly_one_target",
        ),
        CheckConstraint(
            "verification_status IN ('unverified','under_review','verified','stale','rejected')",
            name="verification_status",
        ),
        CheckConstraint(
            "verification_status != 'verified' OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL AND reviewed_fields != '')",
            name="explicit_review",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from",
            name="validity_range",
        ),
        *[
            Index(
                f"uq_verification_{target}_attribution",
                "source_id",
                f"{target}_id",
                unique=True,
                postgresql_where=text("review_field IS NULL"),
            )
            for target in ("university", "program", "scholarship")
        ],
        *[
            Index(
                f"uq_verification_{target}_first_review",
                "source_id",
                f"{target}_id",
                "review_field",
                unique=True,
                postgresql_where=text("review_field IS NOT NULL AND supersedes_id IS NULL"),
            )
            for target in ("university", "program", "scholarship")
        ],
        CheckConstraint(
            "(review_field IS NULL AND value_fingerprint IS NULL AND supersedes_id IS NULL) OR "
            "(review_field IS NOT NULL AND value_fingerprint IS NOT NULL AND "
            "length(value_fingerprint) = 64 AND reviewed_fields = review_field AND "
            "(university_id IS NOT NULL OR program_id IS NOT NULL OR scholarship_id IS NOT NULL) AND "
            "verification_status != 'unverified' AND reviewed_at IS NOT NULL AND "
            "reviewed_by IS NOT NULL AND length(trim(reviewed_by)) > 0)",
            name="field_decision",
        ),
        UniqueConstraint("supersedes_id"),
        UniqueConstraint("source_id", "living_estimate_id"),
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    university_id: Mapped[str | None] = mapped_column(
        ForeignKey("universities.id", ondelete="CASCADE"), index=True
    )
    program_id: Mapped[str | None] = mapped_column(
        ForeignKey("academic_programs.id", ondelete="CASCADE"), index=True
    )
    scholarship_id: Mapped[str | None] = mapped_column(
        ForeignKey("scholarships.id", ondelete="CASCADE"), index=True
    )
    living_estimate_id: Mapped[str | None] = mapped_column(
        ForeignKey("living_cost_estimates.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_fields: Mapped[str] = mapped_column(Text, default="")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, default="")
    review_field: Mapped[str | None] = mapped_column(String(64))
    value_fingerprint: Mapped[str | None] = mapped_column(String(64))
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("verification_records.id"))
    source: Mapped[DataSource] = relationship()
    university: Mapped[University | None] = relationship(back_populates="verifications")
    program: Mapped[AcademicProgram | None] = relationship(back_populates="verifications")
    scholarship: Mapped[Scholarship | None] = relationship(back_populates="verifications")
    living_estimate: Mapped[LivingCostEstimate | None] = relationship(
        back_populates="verifications"
    )


@event.listens_for(Session, "before_flush")
def validate_scholarship_terms(session, flush_context, instances):
    """Validate internal ORM writes too; JSON documents must be replaced on edit."""
    from sqlalchemy import inspect as inspect_state
    from sqlalchemy import select

    from app.schemas.scholarship import ScholarshipTerms, ScopeInput

    affected = {row for row in session.new | session.dirty if isinstance(row, Scholarship)}
    for scope in session.new | session.dirty | session.deleted:
        if not isinstance(scope, ScholarshipScope):
            continue
        state = inspect_state(scope)
        if (
            state.persistent
            and (
                state.attrs.id.history.has_changes()
                or state.attrs.scholarship_id.history.has_changes()
                or state.attrs.scholarship.history.has_changes()
            )
            and scope not in session.deleted
        ):
            raise ValueError("Scope identity and scholarship owner are immutable")
        if scope.scope_extent is None:
            scope.scope_extent = "exact_target"
        if scope not in session.deleted:
            ScopeInput.model_validate(scope)
        parent = scope.scholarship or session.get(Scholarship, scope.scholarship_id)
        if parent:
            affected.add(parent)
            if parent not in session.new:
                # Scope edits participate in the same lock as review decisions.
                session.execute(
                    select(Scholarship.id).where(Scholarship.id == parent.id).with_for_update()
                )
    for row in affected - set(session.deleted):
        values = {
            key: getattr(row, key) for key in ScholarshipTerms.model_fields if key != "scopes"
        }
        values["contract_version"] = row.contract_version or 1
        scopes = [s for s in row.scopes if s not in session.deleted]
        scopes += [
            s
            for s in session.new
            if isinstance(s, ScholarshipScope) and s.scholarship_id == row.id and s not in scopes
        ]
        for scope in scopes:
            scope.scope_extent = scope.scope_extent or "exact_target"
        values["scopes"] = [ScopeInput.model_validate(scope) for scope in scopes]
        terms = ScholarshipTerms.model_validate(values)
        if terms.contract_version == 1 and row.funding_type is None:
            raise ValueError("Legacy scholarships require Full/Partial funding type")
        for scope in scopes:
            model, identifier = next(
                (model, identifier)
                for model, identifier in (
                    (Country, scope.country_id),
                    (University, scope.university_id),
                    (AcademicProgram, scope.program_id),
                )
                if identifier
            )
            target = session.get(model, identifier)
            if target is None or (
                not row.is_demo
                and (
                    getattr(target, "is_demo", False)
                    or isinstance(target, AcademicProgram)
                    and target.university.is_demo
                )
            ):
                raise ValueError(
                    "Scope target must exist and real scholarship cannot target demo data"
                )
            if (
                isinstance(target, AcademicProgram)
                and scope.degree_level
                and scope.degree_level != target.degree_level
            ):
                raise ValueError("Scope degree disagrees with program")
        for key in ("benefits", "requirements", "deadlines"):
            if getattr(row, key) is not None:
                setattr(row, key, terms.model_dump(mode="json")[key])
