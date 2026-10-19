"""Public structured scholarship contract. No private notes, operators or tokens."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.catalog import SourceDTO
from app.schemas.scholarship import ScholarshipTerms


class PublicEvidence(BaseModel):
    field: str
    source: SourceDTO


class ScholarshipPublic(ScholarshipTerms):
    id: str
    name: str
    provider: str
    description: str
    eligibility_summary: str
    coverage: str
    official_url: str | None
    funding_type: Literal["Full", "Partial"] | None
    verification_status: Literal["verified"]
    evidence: list[PublicEvidence]
    scope_labels: dict[str, str]
