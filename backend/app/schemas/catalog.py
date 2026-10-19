from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

Status = Literal["unverified", "under_review", "verified", "stale", "rejected"]
Degree = Literal["Bachelor", "Master", "PhD"]
Period = Literal["year", "semester", "month", "degree"]


class DTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SourceDTO(DTO):
    id: str
    source_type: str
    title: str
    source_url: str | None
    publisher: str
    retrieved_at: datetime | None


class VerificationDTO(DTO):
    entity_type: str
    entity_id: str
    verification_status: Status
    reviewed_at: datetime | None
    reviewed_fields: list[str]
    valid_from: datetime | None
    valid_until: datetime | None
    notes: str
    source: SourceDTO


class ProvenanceDTO(DTO):
    is_demo: bool
    verification_status: Status
    records: list[VerificationDTO]


class CountryDTO(DTO):
    id: str
    name: str
    iso_code: str
    currency_code: str


class CityDTO(DTO):
    id: str
    name: str
    country_id: str


class CostDTO(DTO):
    amount: Decimal
    currency: str
    period: str
    provenance: ProvenanceDTO


class ProgramDTO(DTO):
    id: str
    name: str
    degree_level: Degree
    field_of_study: str
    language_of_instruction: str
    duration_months: int
    tuition_amount: Decimal | None
    tuition_currency: str
    tuition_period: Period
    scholarship_ids: list[str]
    provenance: ProvenanceDTO


class UniversityDTO(DTO):
    id: str
    slug: str
    name: str
    short_name: str
    color: str
    country: CountryDTO
    city: CityDTO
    official_website: str | None
    description: str
    institution_type: str
    status: str
    programs: list[ProgramDTO]
    living_cost: CostDTO | None
    provenance: ProvenanceDTO


class ScholarshipDTO(DTO):
    id: str
    name: str
    provider: str
    description: str
    funding_type: Literal["Full", "Partial"]
    funding_amount: Decimal | None
    funding_currency: str | None
    eligibility_summary: str
    application_deadline: date | None
    official_url: str | None
    coverage: str
    countries: list[CountryDTO]
    degree_levels: list[Degree]
    program_ids: list[str]
    provenance: ProvenanceDTO


class FinancialReferenceDTO(DTO):
    program_id: str
    university_id: str
    university_name: str
    country: CountryDTO
    program_name: str
    tuition_amount: Decimal | None
    tuition_currency: str
    tuition_period: Period
    duration_months: int
    provenance: ProvenanceDTO
    living_cost: CostDTO | None


class PageMeta(DTO):
    page: int
    page_size: int
    total: int
    pages: int


class Page[T](DTO):
    items: list[T]
    meta: PageMeta


class CatalogOptionsDTO(DTO):
    subjects: list[str]
    cities: list[CityDTO]


class ErrorFieldDTO(DTO):
    field: str
    message: str


class ErrorDetailDTO(DTO):
    code: str
    message: str
    fields: list[ErrorFieldDTO] | None = None


class ErrorResponseDTO(DTO):
    error: ErrorDetailDTO


class HealthDTO(DTO):
    status: Literal["ok"]
    service: str
    version: str


class ReadyDTO(DTO):
    status: Literal["ready"]
