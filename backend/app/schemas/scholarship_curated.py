"""Version-2 scholarship-only input; no decisions, eligibility inference or imports."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from app.schemas.curated import (
    EvidenceInput,
    Identifier,
    InputModel,
    SourceInput,
    Text,
    Url,
    safe_url,
)
from app.schemas.scholarship import SCALAR_FIELDS, ScholarshipTerms, field_value, valid_path

Prose = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=10000)
]


class ScholarshipInput(ScholarshipTerms):
    contract_version: Literal[2] = 2
    id: Identifier
    name: Text
    provider: Text
    description: Prose
    funding_type: Literal["Full", "Partial"] | None = None
    # Structured terms must not manufacture legacy totals or a single cutoff.
    funding_amount: None = None
    funding_currency: None = None
    application_deadline: None = None
    eligibility_summary: Prose
    coverage: Prose
    official_url: Url | None = None

    _url = field_validator("official_url")(safe_url)


def supplied_paths(record):
    paths = {p for p in SCALAR_FIELDS if getattr(record, p) is not None}
    for root in ("benefits", "requirements", "deadlines", "scopes"):
        children = getattr(record, root) or {}
        if root == "scopes":
            children = {scope.id: scope for scope in children}
        for key, child in children.items():
            paths.update(
                f"{root}.{key}.{leaf}"
                for leaf, value in child.model_dump().items()
                if leaf != "id" and value is not None
            )
    return paths


class ScholarshipEvidence(EvidenceInput):
    entity_type: Literal["scholarship"]
    fields: list[Annotated[str, StringConstraints(strict=True, min_length=1, max_length=64)]] = (
        Field(min_length=1, max_length=1600)
    )


class ScholarshipBatch(InputModel):
    schema_version: Literal[2]
    scholarships: list[ScholarshipInput] = Field(min_length=1, max_length=50)
    sources: list[SourceInput] = Field(min_length=1, max_length=500)
    evidence: list[ScholarshipEvidence] = Field(min_length=1, max_length=1000)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Schema version must be integer 2")
        return value

    @model_validator(mode="after")
    def relationships(self):
        for rows in (self.scholarships, self.sources):
            if len({r.id for r in rows}) != len(rows):
                raise ValueError("Duplicate IDs within a record type")
        rounds = [(r.scheme_key, r.round_key) for r in self.scholarships]
        scopes = [s.id for r in self.scholarships for s in r.scopes]
        if len(set(rounds)) != len(rounds) or len(set(scopes)) != len(scopes):
            raise ValueError("Duplicate scheme/round or global scope ID")
        targets = {r.id: r for r in self.scholarships}
        sources = {r.id for r in self.sources}
        used, pairs, coverage = set(), set(), {}
        for evidence in self.evidence:
            if evidence.entity_id not in targets or evidence.source_id not in sources:
                raise ValueError("Evidence must link a batch scholarship to a batch source")
            pair = (evidence.entity_id, evidence.source_id)
            if pair in pairs:
                raise ValueError("Duplicate source-to-record evidence")
            pairs.add(pair)
            used.add(evidence.source_id)
            record = targets[evidence.entity_id]
            for path in evidence.fields:
                if not valid_path(path) or field_value(record, path) is None:
                    raise ValueError("Evidence requires an exact known non-null leaf path")
            coverage.setdefault(record.id, set()).update(evidence.fields)
        if used != sources:
            raise ValueError("Every source must be referenced by evidence")
        for row in self.scholarships:
            paths = supplied_paths(row)
            if not all(valid_path(p) for p in paths) or not paths <= coverage.get(row.id, set()):
                raise ValueError("Every supplied factual leaf requires explicit attribution")
        return self
