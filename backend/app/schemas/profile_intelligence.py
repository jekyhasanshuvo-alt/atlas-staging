"""Private, evidence-aware profile/preference contracts; no admissions criteria implied."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.catalog import Degree, PageMeta, Period, SourceDTO, Status
from app.schemas.intelligence import FieldEvidence, IntelligenceRecord


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AssessmentOptions(Strict):
    preferred_degree: Degree | None = None
    teaching_language: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    budget_period: Period | None = None

    @field_validator("teaching_language")
    @classmethod
    def safe_language_text(cls, value):
        if value is not None and any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Comparison text contains unsupported control characters")
        return value


class MatchingQuery(AssessmentOptions):
    q: Annotated[str, Field(max_length=200)] = ""
    university: Annotated[str, Field(max_length=200)] = ""
    verification: Status | None = None
    preference_result: Literal["all", "MATCHES", "DIFFERS", "UNKNOWN"] = "all"
    page: Annotated[int, Field(ge=1, le=10000)] = 1
    page_size: Annotated[int, Field(ge=1, le=20)] = 12

    _safe_search = field_validator("q", "university")(AssessmentOptions.safe_language_text.__func__)


class CompletenessDimension(BaseModel):
    field: str
    label: str
    status: Literal["PROVIDED", "MISSING", "UNSUPPORTED"]
    explanation: str


class Completeness(BaseModel):
    provided: int
    supported: int
    dimensions: list[CompletenessDimension]
    explanation: str


class PreferenceReason(BaseModel):
    attribute: str
    outcome: Literal["MATCH", "DIFFERENT", "UNKNOWN", "NOT_SET"]
    input_used: str | None
    program_value: str | None
    logic: str
    uncertainty: str
    catalog_verification: Status
    evidence: list[FieldEvidence]


class EligibilityCheck(BaseModel):
    category: str
    status: Literal[
        "REQUIREMENT_MET", "REQUIREMENT_NOT_MET", "UNKNOWN", "CONDITIONAL", "NOT_ASSESSED"
    ]
    requirement: str
    student_input_used: dict[str, str | None]
    official_requirement_source: SourceDTO | None
    comparison_logic: str
    uncertainty: str


class Match(BaseModel):
    program: IntelligenceRecord
    preference_result: Literal["MATCHES", "DIFFERS", "UNKNOWN"]
    reasons: list[PreferenceReason]
    eligibility_status: Literal["NOT_ASSESSED"] = "NOT_ASSESSED"
    explanation: str


class MatchPage(BaseModel):
    items: list[Match]
    meta: PageMeta
    explanation: str


class Assessment(Match):
    eligibility_checks: list[EligibilityCheck]
