"""Private identity and workspace records; never serialized as ORM objects."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps


class User(Timestamps, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    account_status: Mapped[str] = mapped_column(String(20), default="active")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("account_status IN ('active', 'disabled')", name="account_status"),
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentProfile(Timestamps, Base):
    __tablename__ = "student_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str] = mapped_column(String(200), default="")
    nationality: Mapped[str] = mapped_column(String(200), default="")
    current_country: Mapped[str] = mapped_column(String(200), default="")
    preferred_destination: Mapped[str] = mapped_column(String(200), default="")
    education_level: Mapped[str] = mapped_column(String(200), default="")
    academic_background: Mapped[str] = mapped_column(String(200), default="")
    preferred_subject: Mapped[str] = mapped_column(String(200), default="")
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    budget_currency: Mapped[str] = mapped_column(String(3), default="CNY")
    language_proficiency: Mapped[str] = mapped_column(String(200), default="")
    scholarship_preference: Mapped[bool] = mapped_column(Boolean, default=False)
    career_goals: Mapped[str] = mapped_column(String(1000), default="")
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("budget_amount >= 0 AND budget_amount <= 100000000", name="budget_range"),
    )


class SavedUniversity(Base):
    __tablename__ = "saved_universities"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    university_id: Mapped[str] = mapped_column(
        ForeignKey("universities.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SavedScholarship(Base):
    __tablename__ = "saved_scholarships"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    scholarship_id: Mapped[str] = mapped_column(
        ForeignKey("scholarships.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentComparison(Base):
    __tablename__ = "student_comparisons"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    university_id: Mapped[str] = mapped_column(
        ForeignKey("universities.id", ondelete="CASCADE"), primary_key=True
    )
    display_order: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("user_id", "display_order"),
        CheckConstraint("display_order >= 0 AND display_order < 4", name="comparison_order"),
    )


class FinancialPlan(Timestamps, Base):
    __tablename__ = "financial_plans"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3))
    country: Mapped[str] = mapped_column(String(200), default="")
    university: Mapped[str] = mapped_column(String(120), default="")
    years: Mapped[int] = mapped_column(Integer)
    tuition: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    accommodation: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    food: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    transportation: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    insurance: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    other: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    scholarship: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    relocation: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    emergency: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    baseline: Mapped[dict | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint("years >= 1 AND years <= 10", name="duration_range"),
        CheckConstraint(
            " AND ".join(
                f"{x} >= 0 AND {x} <= 100000000"
                for x in [
                    "tuition",
                    "accommodation",
                    "food",
                    "transportation",
                    "insurance",
                    "other",
                    "scholarship",
                    "relocation",
                    "emergency",
                ]
            ),
            name="cost_range",
        ),
    )


class StudentChecklistItem(Base):
    __tablename__ = "student_checklist_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(30))
    stable_item_key: Mapped[str] = mapped_column(String(100))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (UniqueConstraint("user_id", "category", "stable_item_key"),)


class DataImportRecord(Base):
    __tablename__ = "data_import_records"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    import_version: Mapped[int] = mapped_column(Integer)
    payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "import_version", "payload_hash"),)


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
