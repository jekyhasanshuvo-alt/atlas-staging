"""Typed scholarship terms and exact leaf paths; no import or award entitlement API."""

from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.curated import Identifier

Label = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
]
Note = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=2000)
]
Key = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9_]{1,16}$")]
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2, allow_inf_nan=False)]
Currency = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]{3}$")]
Positive = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
Degree = Literal["Bachelor", "Master", "PhD"]
# ISO 3166-1 alpha-2; nationality is independent of destination catalog contents.
COUNTRY_CODES = set(
    "AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW".split()
)


class TermsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class Benefit(TermsModel):
    kind: Literal["tuition_waiver", "stipend", "accommodation", "insurance", "travel", "other"]
    label: Label
    coverage_mode: Literal["fixed", "percentage", "full_eligible_cost", "in_kind", "unknown"]
    value_state: Literal["unknown", "estimated", "confirmed"]
    condition_state: Literal["unknown", "conditional", "unconditional"]
    delivery_mode: Literal["waiver", "cash", "reimbursement", "in_kind", "unknown"] = "unknown"
    amount: Money | None = None
    cap_amount: Money | None = None
    percent: (
        Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2, allow_inf_nan=False)]
        | None
    ) = None
    currency: Currency | None = None
    period: Literal["month", "semester", "year", "degree", "one_time"] | None = None
    eligible_cost_basis: Note | None = None
    payment_months: Positive | None = None
    coverage_months: Positive | None = None
    conditions: Note | None = None
    renewal_terms: Note | None = None
    stacking_terms: Note | None = None
    recipient_limit: Positive | None = None

    @model_validator(mode="after")
    def coherent(self):
        if self.value_state == "unknown" and any(
            v is not None for v in (self.amount, self.cap_amount, self.percent)
        ):
            raise ValueError("Unknown value must not contain a monetary quotation")
        if self.condition_state == "conditional" and not self.conditions:
            raise ValueError("Conditional benefit needs conditions")
        if self.coverage_mode == "unknown" and self.value_state != "unknown":
            raise ValueError("Unknown coverage cannot be an exact or estimated term")
        if (
            self.coverage_mode == "fixed"
            and self.value_state != "unknown"
            and (self.amount is None or not self.currency or not self.period)
        ):
            raise ValueError("Known fixed benefit needs amount, currency and period")
        if (
            self.coverage_mode == "percentage"
            and self.value_state != "unknown"
            and (self.percent is None or not self.eligible_cost_basis)
        ):
            raise ValueError("Percentage benefit needs percentage and cost basis")
        if self.coverage_mode == "full_eligible_cost" and not self.eligible_cost_basis:
            raise ValueError("Full eligible coverage needs cost basis")
        if self.percent is not None and self.coverage_mode != "percentage":
            raise ValueError("Percentage requires percentage coverage")
        if self.amount is not None and self.coverage_mode != "fixed":
            raise ValueError("Fixed amount requires fixed coverage")
        if self.cap_amount is not None and (not self.currency or not self.period):
            raise ValueError("Cap needs currency and period")
        return self


class Requirement(TermsModel):
    category: Literal[
        "academic", "language", "age", "nationality", "residency", "employment", "other"
    ]
    statement: Note
    applies_to_country_codes: list[str] | None = Field(default=None, max_length=249)
    nationality_mode: Literal["unknown", "unrestricted", "allowlist", "denylist"] = "unknown"
    nationality_codes: list[str] = Field(default_factory=list, max_length=249)
    conditions: Note | None = None

    @model_validator(mode="after")
    def codes(self):
        for codes in (self.applies_to_country_codes, self.nationality_codes):
            if codes is not None and (
                len(set(codes)) != len(codes) or not set(codes) <= COUNTRY_CODES
            ):
                raise ValueError("Use unique ISO nationality codes")
        if bool(self.nationality_codes) != (self.nationality_mode in {"allowlist", "denylist"}):
            raise ValueError("Nationality lists require an explicit allow/deny mode")
        if self.category != "nationality" and self.nationality_mode != "unknown":
            raise ValueError("Nationality policy belongs to a nationality requirement")
        return self


class Deadline(TermsModel):
    stage: Label
    date: Date | None = None
    closes_at: datetime | None = None
    timezone: Label | None = None
    deadline_state: Literal["known", "rolling", "unknown"]
    conditions: Note | None = None

    @model_validator(mode="after")
    def precision(self):
        if self.deadline_state == "known":
            if (self.date is None) == (self.closes_at is None):
                raise ValueError("Known deadline needs exactly one date or timestamp")
        elif self.date is not None or self.closes_at is not None or self.timezone is not None:
            raise ValueError("Unknown/rolling deadline must not invent a cutoff")
        if self.closes_at is not None:
            if self.closes_at.tzinfo is None or not self.timezone:
                raise ValueError("Exact deadline needs aware timestamp and IANA timezone")
            try:
                zone = ZoneInfo(self.timezone)
            except ZoneInfoNotFoundError as exc:
                raise ValueError("Unknown timezone") from exc
            if self.closes_at.astimezone(zone).utcoffset() != self.closes_at.utcoffset():
                raise ValueError("Timestamp offset disagrees with timezone")
        elif self.timezone is not None:
            raise ValueError("Date-only cutoff must not invent timezone precision")
        return self


class ScopeInput(TermsModel):
    id: Identifier
    country_id: Identifier | None = None
    university_id: Identifier | None = None
    program_id: Identifier | None = None
    degree_level: Degree | None = None
    scope_extent: Literal["exact_target", "descendants"] = "exact_target"

    @model_validator(mode="after")
    def target(self):
        if sum(v is not None for v in (self.country_id, self.university_id, self.program_id)) != 1:
            raise ValueError("Scope needs exactly one destination target")
        if self.program_id and self.scope_extent != "exact_target":
            raise ValueError("A program has no descendant programs")
        return self


class ScholarshipTerms(TermsModel):
    contract_version: Literal[1, 2] = 1
    scheme_key: (
        Annotated[
            str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)
        ]
        | None
    ) = None
    round_key: (
        Annotated[
            str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=80)
        ]
        | None
    ) = None
    intake_label: (
        Annotated[
            str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)
        ]
        | None
    ) = None
    academic_cycle: (
        Annotated[
            str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=40)
        ]
        | None
    ) = None
    intake_start_date: Date | None = None
    cycle_state: Literal["known", "unknown"] | None = None
    provider_kind: Literal["government", "university", "foundation", "other", "unknown"] | None = (
        None
    )
    applicability_state: Literal["unknown", "listed", "unrestricted"] | None = None
    benefits: dict[Key, Benefit] | None = Field(default=None, max_length=20)
    requirements: dict[Key, Requirement] | None = Field(default=None, max_length=40)
    deadlines: dict[Key, Deadline] | None = Field(default=None, max_length=10)
    scopes: list[ScopeInput] = Field(default_factory=list, max_length=100)

    @field_validator("contract_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Contract version must be an integer")
        return value

    @model_validator(mode="after")
    def consistency(self):
        if self.contract_version == 2 and (
            not self.scheme_key
            or not self.round_key
            or not self.cycle_state
            or not self.applicability_state
        ):
            raise ValueError("Structured scholarship requires scheme/round and explicit states")
        if self.cycle_state == "known" and not self.intake_label:
            raise ValueError("Known cycle needs an intake label")
        if self.cycle_state == "unknown" and any(
            (self.intake_label, self.academic_cycle, self.intake_start_date)
        ):
            raise ValueError("Unknown cycle must not contain intake facts")
        if bool(self.scopes) != (self.applicability_state == "listed"):
            raise ValueError("Listed applicability requires scopes; other states forbid them")
        signatures = [
            (s.country_id, s.university_id, s.program_id, s.degree_level, s.scope_extent)
            for s in self.scopes
        ]
        if len(set(signatures)) != len(signatures) or len({s.id for s in self.scopes}) != len(
            self.scopes
        ):
            raise ValueError("Duplicate scope")
        return self


SCALAR_FIELDS = {
    "name",
    "provider",
    "description",
    "funding_type",
    "funding_amount",
    "funding_currency",
    "eligibility_summary",
    "application_deadline",
    "official_url",
    "coverage",
    "intake_label",
    "academic_cycle",
    "intake_start_date",
    "cycle_state",
    "provider_kind",
    "applicability_state",
}
NESTED_FIELDS = {
    "benefits": set(Benefit.model_fields),
    "requirements": set(Requirement.model_fields),
    "deadlines": set(Deadline.model_fields),
    "scopes": set(ScopeInput.model_fields) - {"id"},
}


def valid_path(path):
    if not isinstance(path, str) or len(path) > 64:
        return False
    if path in SCALAR_FIELDS:
        return True
    parts = path.split(".")
    return (
        len(parts) == 3
        and parts[0] in NESTED_FIELDS
        and bool(parts[1])
        and len(parts[1]) <= 36
        and parts[1].isascii()
        and all(c.isalnum() or c in "_-" for c in parts[1])
        and parts[2] in NESTED_FIELDS[parts[0]]
    )


def term_document(entity):
    values = {
        key: getattr(entity, key, None) for key in ScholarshipTerms.model_fields if key != "scopes"
    }
    values["contract_version"] = values["contract_version"] or 1
    values["scopes"] = [ScopeInput.model_validate(scope).model_dump() for scope in entity.scopes]
    return ScholarshipTerms.model_validate(values)


def field_value(entity, path):
    if not valid_path(path):
        raise ValueError("Unsupported scholarship field path")
    if path in SCALAR_FIELDS:
        return getattr(entity, path, None)
    root, key, leaf = path.split(".")
    document = term_document(entity).model_dump(mode="json")
    collection = document[root] or {}
    if root == "scopes":
        collection = {scope["id"]: scope for scope in collection}
    if key not in collection:
        raise ValueError("Missing scholarship claim")
    return collection[key][leaf]
