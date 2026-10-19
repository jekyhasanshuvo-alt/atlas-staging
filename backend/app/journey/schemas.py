"""Experimental personal tracking. No factual admissions/document assertions."""

import re
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    create_model,
    field_validator,
    model_validator,
)

Stage = Literal[
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
]
DocumentState = Literal["NOT_STARTED", "IN_PROGRESS", "READY", "SUBMITTED", "NOT_APPLICABLE"]
Identifier = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9_-]{1,36}$")]
Title = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=160)
]
Key = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=80)
]
Reason = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=500)
]
Description = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=2000)
]
Version = Annotated[int, Field(strict=True, ge=1)]
Timezone = Annotated[
    str,
    StringConstraints(
        strict=True, pattern=r"^(?:UTC|[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+)$", max_length=80
    ),
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @field_validator("*")
    @classmethod
    def safe_personal_text(cls, value):
        if isinstance(value, str) and (
            any(ord(c) < 32 or ord(c) == 127 for c in value)
            or re.search(r"(?i)(https?://|file:|data:|blob:|s3:|www\.)", value)
        ):
            raise ValueError(
                "Use plain planning text; controls and document/website URLs are not accepted"
            )
        return value


class ApplicationCreate(Strict):
    label: Title
    university_id: Identifier
    program_id: Identifier | None = None
    cycle_key: Key | None = None
    route_key: Key | None = None


class ApplicationPatch(Strict):
    expected_version: Version
    label: Title | None = None
    university_id: Identifier | None = None
    program_id: Identifier | None = None
    cycle_key: Key | None = None
    route_key: Key | None = None
    archived: StrictBool | None = None


class StageChange(Strict):
    expected_version: Version
    stage: Stage
    reason: Reason | None = None


class DeleteApplication(Strict):
    expected_version: Version
    confirmation: Literal["DELETE APPLICATION"]


class ApplicationRead(ApplicationCreate):
    id: UUID
    stage: Stage
    archived: StrictBool
    version: Version
    created_at: AwareDatetime
    updated_at: AwareDatetime
    link_available: StrictBool
    stage_basis: Literal["user_managed_not_verified"] = "user_managed_not_verified"
    official_requirements: Literal["UNKNOWN"] = "UNKNOWN"
    official_deadline: Literal["UNKNOWN"] = "UNKNOWN"


class EventRead(Strict):
    id: UUID
    application_id: UUID
    previous_stage: Stage | None
    new_stage: Stage
    version: Version
    changed_at: AwareDatetime
    reason: Reason | None
    basis: Literal["user_managed_not_verified"] = "user_managed_not_verified"


class ItemCreate(Strict):
    kind: Literal["task", "document", "reminder", "note"]
    title: Title
    description: Description | None = None
    completed: StrictBool | None = None
    priority: Literal["low", "normal", "high"] | None = None
    document_state: DocumentState | None = None
    due_date: date | None = None
    reminder_mode: Literal["date", "instant"] | None = None
    reminder_date: date | None = None
    reminder_at: AwareDatetime | None = None
    timezone: Timezone | None = None

    @model_validator(mode="after")
    def kind_fields(self):
        if self.kind == "task":
            self.completed = False if self.completed is None else self.completed
            self.priority = self.priority or "normal"
            valid = (
                self.document_state is None
                and self.reminder_mode is None
                and self.reminder_date is None
                and self.reminder_at is None
                and ((self.due_date is None) == (self.timezone is None))
            )
        elif self.kind == "document":
            self.document_state = self.document_state or "NOT_STARTED"
            valid = all(
                getattr(self, f) is None
                for f in (
                    "completed",
                    "priority",
                    "due_date",
                    "reminder_mode",
                    "reminder_date",
                    "reminder_at",
                    "timezone",
                )
            )
        elif self.kind == "reminder":
            self.completed = False if self.completed is None else self.completed
            valid = (
                self.timezone is not None
                and self.priority is None
                and self.document_state is None
                and self.due_date is None
                and (
                    (
                        self.reminder_mode == "date"
                        and self.reminder_date is not None
                        and self.reminder_at is None
                    )
                    or (
                        self.reminder_mode == "instant"
                        and self.reminder_at is not None
                        and self.reminder_date is None
                    )
                )
            )
        else:
            valid = all(
                getattr(self, f) is None
                for f in (
                    "completed",
                    "priority",
                    "document_state",
                    "due_date",
                    "reminder_mode",
                    "reminder_date",
                    "reminder_at",
                    "timezone",
                )
            )
        if not valid:
            raise ValueError(
                "Planning item fields do not match its kind; dates need explicit timezone"
            )
        return self


ItemPatch = create_model(
    "ItemPatch",
    __base__=Strict,
    expected_version=(Version, ...),
    **{
        name: (field.annotation | None, None)
        for name, field in ItemCreate.model_fields.items()
        if name != "kind"
    },
)


class ItemRead(ItemCreate):
    id: UUID
    application_id: UUID
    version: Version
    created_at: AwareDatetime
    updated_at: AwareDatetime
    origin: Literal["personal_user_created"] = "personal_user_created"


class PageMeta(Strict):
    page: Annotated[int, Field(strict=True, ge=1)]
    page_size: Annotated[int, Field(strict=True, ge=1)]
    total: Annotated[int, Field(strict=True, ge=0)]
    pages: Annotated[int, Field(strict=True, ge=0)]


class Page[T](Strict):
    items: list[T]
    meta: PageMeta


class Dashboard(Strict):
    total_applications: int
    archived_applications: int
    by_stage: dict[str, int]
    pending_personal_tasks: int
    completed_personal_tasks: int
    overdue_personal_tasks: int
    upcoming_personal_reminders: list[ItemRead]
    recent_personal_events: list[EventRead]
    missing_cycle: int
    missing_program: int
    official_requirements: Literal["UNKNOWN"] = "UNKNOWN"
    explanation: str
