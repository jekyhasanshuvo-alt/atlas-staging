"""Internal experimental contracts. These are not approved collection/public APIs."""

import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    create_model,
    field_validator,
    model_validator,
)

Text80 = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=80)
]
Text120 = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)
]
Text200 = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
]
Identifier = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9_-]{1,36}$")]
Country = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]{2}$")]
Currency = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]{3}$")]
Degree = Literal["Bachelor", "Master", "PhD"]
Period = Literal["month", "semester", "year", "degree"]
Version = Annotated[int, Field(strict=True, ge=1)]


def decimal_input(value):
    if (
        not isinstance(value, (str, Decimal))
        or isinstance(value, str)
        and not re.fullmatch(r"\d{1,9}(?:\.\d{1,4})?", value)
    ):
        raise ValueError("Use an exact nonnegative decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        raise ValueError("Use an exact decimal string") from None
    if not parsed.is_finite():
        raise ValueError("Finite decimal required")
    return parsed


Score = Annotated[Decimal, BeforeValidator(decimal_input), Field(ge=0, lt=100000, decimal_places=4)]
Money = Annotated[
    Decimal, BeforeValidator(decimal_input), Field(ge=0, le=100000000, decimal_places=2)
]


class Internal(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @field_validator("*")
    @classmethod
    def text_safety(cls, value):
        if isinstance(value, str) and any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("Control characters are not supported")
        return value


class Reference(Internal):
    id: Identifier


class SavedSummary(Internal):
    id: Identifier
    name: Text200


class SavedRead(Internal):
    id: Identifier
    created_at: AwareDatetime
    availability: Literal["available", "unavailable"]
    program: SavedSummary | None


class AcademicCreate(Internal):
    credential_level: Text80 | None = None
    qualification_type: Text120 | None = None
    institution: Text200 | None = None
    country_code: Country | None = None
    subject: Text200 | None = None
    completion_status: Literal["unknown", "in_progress", "completed", "incomplete"] = "unknown"
    award_date: date | None = None
    grade_value: Text80 | None = None
    grade_scale: Text120 | None = None
    maximum_grade: (
        Annotated[
            Decimal, BeforeValidator(decimal_input), Field(gt=0, lt=100000000, decimal_places=4)
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def grade_and_dates(self):
        if self.award_date and (
            self.award_date > datetime.now(UTC).date() or self.completion_status != "completed"
        ):
            raise ValueError("Award date requires completed status and cannot be future")
        if self.grade_value is None:
            if self.grade_scale is not None or self.maximum_grade is not None:
                raise ValueError("Omit scale and maximum when grade is unknown")
        elif self.grade_scale is None:
            raise ValueError("Original grade scale required")
        elif self.grade_scale == "letter":
            if self.maximum_grade is not None or not re.fullmatch(
                r"[A-Za-z][A-Za-z+ -]{0,79}", self.grade_value
            ):
                raise ValueError("Letter grades require literal letters and no numeric maximum")
        else:
            maximum = declared_maximum(self.grade_scale)
            value = decimal_input(self.grade_value)
            if value > maximum or self.maximum_grade != maximum:
                raise ValueError("Numeric grade must fit its explicit original scale and maximum")
        return self


def declared_maximum(scale):
    # Experimental syntax only: no approved institutional/test equivalence registry.
    if not isinstance(scale, str) or not re.fullmatch(r"0\.\.\d{1,8}(?:\.\d{1,4})?", scale):
        raise ValueError("Unsupported scale: use an explicit 0..maximum or letter grade")
    maximum = Decimal(scale[3:])
    if not 0 < maximum < 100000000:
        raise ValueError("Invalid declared scale")
    return maximum


class Component(Internal):
    component: Text80
    score: Score
    score_scale: Text120

    @model_validator(mode="after")
    def in_declared_scale(self):
        if self.score > declared_maximum(self.score_scale):
            raise ValueError("Score exceeds the explicit original scale")
        return self


class LanguageCreate(Internal):
    test_type: Text80 | None = None
    test_version: Text80 | None = None
    test_date: date | None = None
    overall_score: Score | None = None
    score_scale: Text120 | None = None
    expires_on: date | None = None
    components: list[Component] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def scores_and_dates(self):
        if self.test_date and self.test_date > datetime.now(UTC).date():
            raise ValueError("Test date cannot be future")
        if self.expires_on and (not self.test_date or self.expires_on < self.test_date):
            raise ValueError("Expiry needs an ordered test date")
        if self.overall_score is not None and (
            self.score_scale is None or self.overall_score > declared_maximum(self.score_scale)
        ):
            raise ValueError("Score requires its explicit compatible original scale")
        if self.overall_score is None and self.score_scale is not None:
            raise ValueError("Unknown score has no declared scale")
        names = [c.component.casefold() for c in self.components]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate component names")
        return self


def patch_contract(name, source):
    return create_model(
        name,
        __base__=Internal,
        expected_version=(Version, ...),
        **{key: (field.annotation | None, None) for key, field in source.model_fields.items()},
    )


AcademicPatch = patch_contract("AcademicPatch", AcademicCreate)
LanguagePatch = patch_contract("LanguagePatch", LanguageCreate)


class AcademicRead(AcademicCreate):
    id: UUID
    version: Version
    evidence_status: Literal["self_reported"]
    created_at: AwareDatetime
    updated_at: AwareDatetime


class LanguageRead(LanguageCreate):
    id: UUID
    version: Version
    evidence_status: Literal["self_reported"]
    created_at: AwareDatetime
    updated_at: AwareDatetime


class Budget(Internal):
    amount: Money
    currency: Currency
    period: Period


class IntakeWindow(Internal):
    start: date | None
    end: date | None

    @model_validator(mode="after")
    def ordered(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError("Intake window must be ordered")
        return self


class PreferencesReplace(Internal):
    expected_version: Annotated[int, Field(strict=True, ge=0)]
    countries: list[Country] = Field(max_length=20)
    degrees: list[Degree] = Field(max_length=20)
    interests: list[Text200] = Field(max_length=20)
    teaching_languages: list[Text200] = Field(max_length=20)
    budget: Budget | None
    intake_window: IntakeWindow | None

    @field_validator("countries", "degrees", "interests", "teaching_languages")
    @classmethod
    def unique_choices(cls, values):
        if len({v.casefold() for v in values}) != len(values):
            raise ValueError("Duplicate preference choices")
        return values


class PreferencesRead(Internal):
    version: Annotated[int, Field(strict=True, ge=0)]
    updated_at: AwareDatetime | None
    countries: list[Country]
    degrees: list[Degree]
    interests: list[Text200]
    teaching_languages: list[Text200]
    budget: Budget | None
    intake_window: IntakeWindow | None


class ValueState[T](Internal):
    state: Literal["known", "unknown", "not_applicable"]
    value: T | None
    reason: Text200 | None

    @model_validator(mode="after")
    def coherent(self):
        if self.state == "known":
            if self.value is None or self.reason is not None:
                raise ValueError("Known state needs value and no unknown reason")
        elif self.value is not None or self.reason is None:
            raise ValueError("Unknown/not-applicable needs null value and reason")
        return self


class Intake(Internal):
    program_id: Identifier
    cycle_key: Text80
    round_key: Text80


class Deadline(Internal):
    state: Literal["unknown", "not_announced", "rolling", "known_date", "known_instant"]
    date: date | None
    instant: AwareDatetime | None
    explanation: Text200 | None

    @model_validator(mode="after")
    def precision(self):
        if self.state == "known_date":
            valid = self.date is not None and self.instant is None
        elif self.state == "known_instant":
            valid = self.instant is not None and self.date is None
        else:
            valid = self.date is None and self.instant is None and self.explanation is not None
        if not valid:
            raise ValueError("Deadline precision/state mismatch")
        return self


class Stage(Internal):
    stage_key: Text80
    action: Literal["submission", "receipt", "nomination", "payment", "interview", "other"]
    condition: ValueState[Text200]
    opens: Deadline
    closes: Deadline


class RuleBase(Internal):
    rule_key: Text80
    applicability: ValueState[Text200]
    stage_key: Text80 | None


class QualificationRule(RuleBase):
    kind: Literal["qualification"]
    category: ValueState[Text120]
    system: ValueState[Text120]
    recognition_policy: ValueState[Text200]


class GradeRule(RuleBase):
    kind: Literal["grade"]
    system: ValueState[Text120]
    scale: ValueState[Text120]
    component: ValueState[Text80]
    operator: Literal["exact_equal", "gte", "lte", "range"]
    minimum: ValueState[Score]
    maximum: ValueState[Score]


class LanguageRule(RuleBase):
    kind: Literal["language"]
    test: ValueState[Text80]
    provider_version: ValueState[Text120]
    overall: ValueState[Score]
    scale: ValueState[Text120]
    components: list[Component] = Field(max_length=20)
    validity_basis: ValueState[Text200]


class NationalityRule(RuleBase):
    kind: Literal["nationality"]
    mode: Literal["listed", "excluded", "unrestricted", "unknown"]
    countries: list[Country] = Field(max_length=250)
    route_conditions: ValueState[Text200]

    @model_validator(mode="after")
    def list_state(self):
        if (self.mode in {"listed", "excluded"}) != bool(self.countries):
            raise ValueError("Nationality list must match its explicit mode")
        if len(set(self.countries)) != len(self.countries):
            raise ValueError("Duplicate nationality codes")
        return self


class DocumentRule(RuleBase):
    kind: Literal["documents"]
    document_type: ValueState[Text120]
    required: Literal["required", "conditional", "not_applicable", "unknown"]
    format_translation: ValueState[Text200]


class GroupRule(RuleBase):
    kind: Literal["group"]
    operator: Literal["all_of", "any_of"]
    children: list[Text80] = Field(min_length=1, max_length=100)


class ConditionRule(RuleBase):
    kind: Literal["condition"]
    predicate: ValueState[Text200]
    consequent: Text80


Rule = Annotated[
    QualificationRule
    | GradeRule
    | LanguageRule
    | NationalityRule
    | DocumentRule
    | GroupRule
    | ConditionRule,
    Field(discriminator="kind"),
]


class IntakeFacts(Internal):
    year: ValueState[Annotated[int, Field(strict=True, ge=1900, le=2200)]]
    term: ValueState[Text80]
    academic_cycle: ValueState[Text80]
    country_id: Identifier
    degree: Degree


class AdmissionsFacts(Internal):
    intake: IntakeFacts
    stages: list[Stage] = Field(max_length=20)
    requirements: list[Rule] = Field(max_length=100)
    gaps: list[Text200] = Field(max_length=50)

    @model_validator(mode="after")
    def graph(self):
        nodes = {r.rule_key: r for r in self.requirements}
        stages = {s.stage_key for s in self.stages}
        if len(nodes) != len(self.requirements) or len(stages) != len(self.stages):
            raise ValueError("Duplicate rule/stage keys")

        def walk(key, ancestors):
            if key not in nodes or key in ancestors or len(ancestors) >= 5:
                raise ValueError("Unsupported cyclic/deep/missing rule graph")
            rule = nodes[key]
            if rule.stage_key is not None and rule.stage_key not in stages:
                raise ValueError("Unknown rule stage")
            children = (
                rule.children
                if isinstance(rule, GroupRule)
                else [rule.consequent]
                if isinstance(rule, ConditionRule)
                else []
            )
            if len(set(children)) != len(children):
                raise ValueError("Duplicate rule branches")
            for child in children:
                walk(child, ancestors | {key})

        for key in nodes:
            walk(key, set())
        return self


class EvidenceInput(Internal):
    version_id: UUID
    source_id: Identifier
    capture_id: UUID
    field_path: Annotated[
        str, StringConstraints(strict=True, min_length=2, max_length=200, pattern=r"^/\S+$")
    ]
    locator: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=500)
    ]
    excerpt: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=10000)
    ]


class CorrectionPublic(Internal):
    id: UUID
    predecessor_id: UUID | None
    created_at: AwareDatetime
    evidence_references: list[UUID]
    # Deliberately no actor, reviewer, private reason, digest or arbitrary payload.


class ReviewBindingInput(Internal):
    evidence_id: UUID
    version_id: UUID
    source_id: Identifier
    review_id: Text80


class CaptureMetadata(Internal):
    source_url: Annotated[str, StringConstraints(strict=True, max_length=2000)]
    title: Text200
    publisher: Text200
    source_type: Literal["official"]
    retrieved_at: AwareDatetime
    publication_date: date | None
    update_date: date | None
    program_id: Identifier
    cycle_key: Text80
    round_key: Text80
    mime_type: Literal["text/html", "application/pdf", "text/plain"]
    byte_length: Annotated[int, Field(strict=True, ge=1, le=10000000)]
    artifact_ref: UUID  # Opaque store identity, never a file path/student URL.

    @field_validator("source_url")
    @classmethod
    def official_url(cls, value):
        from app.schemas.curated import safe_url

        return safe_url(value)

    @field_validator("retrieved_at")
    @classmethod
    def actual_retrieval(cls, value):
        if value > datetime.now(UTC):
            raise ValueError("Future retrieval is not evidence")
        return value


class CaptureInput(Internal):
    source_id: Identifier
    metadata: CaptureMetadata
    content_sha256: Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
    captured_at: AwareDatetime
