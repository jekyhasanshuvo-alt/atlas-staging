"""Public catalog intelligence. No internal review/audit payloads."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.catalog import CityDTO, CountryDTO, Degree, Period, SourceDTO, Status


class FieldEvidence(BaseModel):
    source: SourceDTO
    evidence_reference: str
    verification_status: Status
    reviewed_at: datetime | None


class Fact(BaseModel):
    value: str | int | Decimal | None
    verification_status: Status
    evidence: list[FieldEvidence]
    caveat: str


class IntelligenceRecord(BaseModel):
    id: str
    kind: Literal["university", "program"]
    name: str
    country: CountryDTO
    city: CityDTO
    is_demo: bool
    verification_status: Status
    facts: dict[str, Fact]
    university_id: str | None = None
    university_name: str | None = None
    degree_level: Degree | None = None
    field_of_study: str | None = None
    language_of_instruction: str | None = None
    duration_months: int | None = None
    tuition_amount: Decimal | None = None
    tuition_currency: str | None = None
    tuition_period: Period | None = None
    institution_type: str | None = None
    official_website: str | None = None
    description: str | None = None


class Comparison(BaseModel):
    items: list[IntelligenceRecord]
    unavailable_ids: list[str]
