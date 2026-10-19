from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    create_model,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class EmailInput(StrictModel):
    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalize(cls, value):
        return value.strip().lower()


class Credentials(EmailInput):
    password: str = Field(min_length=12, max_length=128)


class Registration(Credentials):
    @field_validator("password")
    @classmethod
    def strength(cls, value):
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Use at least 12 characters including a letter and a number")
        return value


class TokenInput(StrictModel):
    token: str = Field(min_length=40, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class ResetInput(TokenInput):
    password: str = Field(min_length=12, max_length=128)

    _strength = field_validator("password")(Registration.strength.__func__)


Money = Annotated[Decimal, Field(ge=0, le=100000000, decimal_places=2, allow_inf_nan=False)]
Text = Annotated[str, Field(max_length=200)]


class ProfilePatch(StrictModel):
    full_name: Text | None = None
    nationality: Text | None = None
    current_country: Text | None = None
    preferred_destination: Text | None = None
    education_level: Text | None = None
    academic_background: Text | None = None
    preferred_subject: Text | None = None
    budget_amount: Money | None = None
    budget_currency: Literal["CNY", "USD", "BDT"] | None = None
    language_proficiency: Text | None = None
    scholarship_preference: bool | None = None
    career_goals: Annotated[str, Field(max_length=1000)] | None = None
    complete_onboarding: bool = False

    @field_validator(
        "full_name",
        "nationality",
        "current_country",
        "preferred_destination",
        "education_level",
        "academic_background",
        "preferred_subject",
        "language_proficiency",
        "career_goals",
    )
    @classmethod
    def clean_profile_text(cls, value, info: ValidationInfo):
        if value is None:
            return value
        allowed = (
            {"\n", "\t"}
            if info.field_name in {"academic_background", "language_proficiency", "career_goals"}
            else set()
        )
        if any((ord(char) < 32 and char not in allowed) or ord(char) == 127 for char in value):
            raise ValueError("Profile text contains unsupported control characters")
        return value.strip()

    @model_validator(mode="after")
    def no_explicit_null(self):
        if any(getattr(self, f) is None for f in self.model_fields_set):
            raise ValueError("Omit unchanged fields; null is not supported")
        return self


class PlanValues(StrictModel):
    currency: Literal["CNY", "USD", "BDT"]
    country: Text
    university: str = Field(max_length=120)
    years: int = Field(ge=1, le=10)
    tuition: Money
    accommodation: Money
    food: Money
    transportation: Money
    insurance: Money
    other: Money
    scholarship: Money
    relocation: Money
    emergency: Money


class PlanCreate(PlanValues):
    name: str = Field(min_length=1, max_length=120)
    baseline: PlanValues | None = None

    @field_validator("name")
    @classmethod
    def meaningful_name(cls, value):
        if not value.strip():
            raise ValueError("Enter a plan name")
        return value.strip()


PlanUpdate = create_model(
    "PlanUpdate",
    __base__=StrictModel,
    version=(Annotated[int, Field(ge=1)], ...),
    **{
        name: (field.rebuild_annotation() | None, None)
        for name, field in PlanCreate.model_fields.items()
    },
)


class ReferenceInput(StrictModel):
    id: str = Field(min_length=1, max_length=120)


class ComparisonInput(StrictModel):
    ids: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(max_length=4)

    @field_validator("ids")
    @classmethod
    def unique(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Duplicate university IDs")
        return value


CHECKLISTS = {
    "preparation": {"profile", "shortlist", "funding", "documents"},
    "life-checklist": {"passport", "arrival", "housing", "transport", "banking", "health"},
    "career-checklist": {"explore", "skills", "cv", "internship", "pathways"},
}


class ChecklistInput(StrictModel):
    category: Literal["preparation", "life-checklist", "career-checklist"]
    completed: list[str] = Field(max_length=20)

    @model_validator(mode="after")
    def known_keys(self):
        if not set(self.completed) <= CHECKLISTS[self.category]:
            raise ValueError("Unknown checklist task")
        return self


class ImportPayload(StrictModel):
    import_version: Literal[1]
    profile: ProfilePatch | None = None
    universities: list[Annotated[str, Field(max_length=120)]] = Field(
        default_factory=list, max_length=100
    )
    scholarships: list[Annotated[str, Field(max_length=120)]] = Field(
        default_factory=list, max_length=100
    )
    comparison: ComparisonInput | None = None
    financial_plan: PlanCreate | None = None
    checklists: list[ChecklistInput] = Field(default_factory=list, max_length=3)


class ImportInput(StrictModel):
    payload: ImportPayload
    confirmed: bool = False


class DeleteAccount(StrictModel):
    password: str = Field(max_length=128)
    confirmation: Literal["DELETE MY ACCOUNT"]
