"""Bounded curator input, independent of public API DTOs and review workflows."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
    field_validator,
    model_validator,
)

MAX_FILE_BYTES = 1_048_576
Identifier = Annotated[
    str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$", max_length=36)
]
Text = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
]
Url = Annotated[str, StringConstraints(strict=True, max_length=2048)]
UNIVERSITY_FIELDS = {
    "name",
    "short_name",
    "country_id",
    "city_id",
    "official_website",
    "description",
    "institution_type",
}
PROGRAM_FIELDS = {
    "name",
    "university_id",
    "degree_level",
    "field_of_study",
    "language_of_instruction",
    "duration_months",
    "tuition_amount",
    "tuition_currency",
    "tuition_period",
}


def safe_url(value: str | None):
    if value is None:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Use an absolute HTTP(S) URL with a hostname")
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value) or "\\" in value:
        raise ValueError("Use a credential-free HTTP(S) URL without whitespace or backslashes")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Source URLs must not contain credentials")
    TypeAdapter(HttpUrl).validate_python(value)
    return value  # Preserve supplied URL, rather than changing exact-replay comparisons.


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UniversityInput(InputModel):
    id: Identifier
    slug: Annotated[
        str, StringConstraints(strict=True, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    ]
    name: Text
    short_name: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=12)
    ]
    country_id: Identifier
    city_id: Identifier
    official_website: Url | None = None
    description: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=10000)
    ]
    institution_type: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=50)
    ]
    color: Literal["blue", "teal", "violet", "amber", "rose"] = "blue"

    _url = field_validator("official_website")(safe_url)


class ProgramInput(InputModel):
    id: Identifier
    university_id: Identifier
    name: Text
    degree_level: Literal["Bachelor", "Master", "PhD"]
    field_of_study: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)
    ]
    language_of_instruction: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)
    ]
    duration_months: Annotated[int, Field(strict=True, gt=0, le=2147483647)]
    tuition_amount: (
        Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2, allow_inf_nan=False)] | None
    ) = None
    tuition_currency: Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]{3}$")]
    tuition_period: Literal["year", "semester", "month", "degree"]


class SourceInput(InputModel):
    id: Identifier
    source_type: Literal["official", "publication", "other"]
    title: Text
    source_url: Url
    publisher: Text
    retrieved_at: AwareDatetime

    _url = field_validator("source_url")(safe_url)

    @field_validator("retrieved_at")
    @classmethod
    def actual_retrieval(cls, value):
        if value > datetime.now(UTC):
            raise ValueError("Retrieval time cannot be in the future")
        return value.astimezone(UTC)


class EvidenceInput(InputModel):
    entity_type: Literal["university", "program"]
    entity_id: Identifier
    source_id: Identifier
    fields: list[Text] = Field(min_length=1, max_length=16)
    notes: Annotated[str, StringConstraints(strict=True, max_length=2000)] | None = None

    @field_validator("fields")
    @classmethod
    def unique_fields(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Duplicate attributed fields")
        return sorted(value)


class CuratedBatch(InputModel):
    schema_version: Literal[1]
    universities: list[UniversityInput] = Field(max_length=50)
    programs: list[ProgramInput] = Field(max_length=250)
    sources: list[SourceInput] = Field(min_length=1, max_length=500)
    evidence: list[EvidenceInput] = Field(min_length=1, max_length=1000)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Schema version must be integer 1")
        return value

    @model_validator(mode="after")
    def relationships(self):
        if not self.universities and not self.programs:
            raise ValueError("Supply at least one university or program")
        for records in (self.universities, self.programs, self.sources):
            if len({record.id for record in records}) != len(records):
                raise ValueError("Duplicate IDs within a record type")
        if {u.id for u in self.universities} & {p.id for p in self.programs}:
            raise ValueError("University and program IDs must be distinct")
        if len({u.slug for u in self.universities}) != len(self.universities):
            raise ValueError("Duplicate university slugs")
        targets = {
            **{("university", u.id): u for u in self.universities},
            **{("program", p.id): p for p in self.programs},
        }
        sources = {source.id for source in self.sources}
        pairs, used_sources, coverage = set(), set(), {}
        for evidence in self.evidence:
            target = (evidence.entity_type, evidence.entity_id)
            if target not in targets or evidence.source_id not in sources:
                raise ValueError("Evidence must link a batch record to a batch source")
            pair = (*target, evidence.source_id)
            if pair in pairs:
                raise ValueError("Duplicate source-to-record evidence")
            pairs.add(pair)
            used_sources.add(evidence.source_id)
            allowed = UNIVERSITY_FIELDS if evidence.entity_type == "university" else PROGRAM_FIELDS
            if not set(evidence.fields) <= allowed:
                raise ValueError("Unknown attributed field for target type")
            if any(getattr(targets[target], field) is None for field in evidence.fields):
                raise ValueError("Unknown/null facts must not be attributed as supplied values")
            coverage.setdefault(target, set()).update(evidence.fields)
        if used_sources != sources:
            raise ValueError("Every source must be referenced by evidence")
        for target, record in targets.items():
            fields = UNIVERSITY_FIELDS if target[0] == "university" else PROGRAM_FIELDS
            supplied = {field for field in fields if getattr(record, field) is not None}
            if not supplied <= coverage.get(target, set()):
                raise ValueError(
                    "Every supplied factual field requires explicit source attribution"
                )
        return self


def load_batch(path: str | Path):
    with Path(path).open("rb") as file:
        raw = file.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("Import file exceeds 1 MiB")

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON object key")
            result[key] = value
        return result

    def invalid_number(value):
        raise ValueError("Non-finite JSON numbers are not allowed")

    document = json.loads(
        raw.decode("utf-8-sig"),
        parse_float=Decimal,
        parse_constant=invalid_number,
        object_pairs_hook=unique_keys,
    )
    if (
        isinstance(document, dict)
        and type(document.get("schema_version")) is int
        and document["schema_version"] == 2
    ):
        from app.schemas.scholarship_curated import ScholarshipBatch

        return ScholarshipBatch.model_validate(document)
    return CuratedBatch.model_validate(document)
