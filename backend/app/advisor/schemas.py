from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.catalog import Status
from app.schemas.financial_scenario import ScenarioInput, ScenarioResult

Text = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=1200)
]
Label = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)
]
Identifier = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9_-]{1,36}$")]
Intent = Literal[
    "auto",
    "university",
    "program",
    "compare",
    "scholarship",
    "matching",
    "financial",
    "planning",
    "eligibility",
    "unsupported",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Preferences(Strict):
    degree: Literal["Bachelor", "Master", "PhD"] | None = None
    subject: Label | None = None
    language: Label | None = None

    @field_validator("*")
    @classmethod
    def plain_text(cls, value):
        if value is not None and any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("Use plain preference text")
        return value


class Ask(Strict):
    question: Text
    intent: Intent = "auto"
    entity_ids: Annotated[list[Identifier], Field(max_length=4)] = []
    search: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, max_length=120)
    ] = ""
    preferences: Preferences | None = None
    scenario: ScenarioInput | None = None
    personal_stage: (
        Literal[
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
        | None
    ) = None

    @field_validator("question", "search")
    @classmethod
    def controls(cls, value):
        if any((ord(c) < 32 and c not in "\n\t") or ord(c) == 127 for c in value):
            raise ValueError("Unsupported control character")
        return value

    @model_validator(mode="after")
    def distinct(self):
        if len(self.entity_ids) != len(set(self.entity_ids)):
            raise ValueError("Select distinct catalog IDs")
        if self.scenario is not None and self.intent not in {"auto", "financial"}:
            raise ValueError("Scenario context requires financial intent")
        return self


class Citation(Strict):
    id: str
    review_context: str
    entity_id: str
    entity_kind: Literal["university", "program", "scholarship"]
    field: str
    source_id: str
    source_title: str
    source_url: str | None
    publisher: str
    source_type: str
    retrieved_at: datetime | None
    reviewed_at: datetime | None
    verification_status: Status
    role: Literal["supports_stored_field", "context_only"]
    freshness: Literal["stored_snapshot_current_review", "freshness_unknown", "not_current_support"]
    intake: None = None
    capture_timestamp: None = None
    applicability: str = "Exact stored field only; current intake applicability is not established."


class Claim(Strict):
    id: str
    text: Annotated[str, Field(max_length=1600)]
    entity_id: str | None = None
    field: str | None = None
    value: str | None = None
    basis: Literal[
        "stored_catalog",
        "supported_stored_field",
        "general_guidance",
        "explicit_user_preference",
        "hypothetical_scenario",
        "user_managed_stage",
    ]
    verification_status: Status = "unverified"
    supporting_citation_ids: list[str] = []
    context_citation_ids: list[str] = []


class Answer(Strict):
    status: Literal[
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "INSUFFICIENT_EVIDENCE",
        "UNSUPPORTED",
        "SAFETY_REFUSAL",
        "INTERNAL_ERROR",
    ]
    code: Literal[
        "ADVISOR_OK",
        "ADVISOR_PARTIAL",
        "ADVISOR_EVIDENCE_MISSING",
        "ADVISOR_UNSUPPORTED",
        "ADVISOR_REFUSED",
        "ADVISOR_INTERNAL",
    ]
    intent: Intent
    scope: Literal["general", "selected_catalog", "request_scoped"]
    summary: str
    claims: Annotated[list[Claim], Field(max_length=64)] = []
    citations: Annotated[list[Citation], Field(max_length=64)] = []
    unknowns: list[str] = []
    limitations: list[str] = []
    follow_ups: list[str] = []
    unavailable_ids: list[str] = []
    scenario_result: ScenarioResult | None = None
    eligibility_status: Literal["NOT_ASSESSED"] = "NOT_ASSESSED"
    provider: Literal["offline_rules_v1"] = "offline_rules_v1"
    external_inference: Literal[False] = False
    conversation_stored: Literal[False] = False
    live_sources_fetched: Literal[False] = False

    @model_validator(mode="after")
    def citations_bound(self):
        expected = {
            "SUPPORTED": "ADVISOR_OK",
            "PARTIALLY_SUPPORTED": "ADVISOR_PARTIAL",
            "INSUFFICIENT_EVIDENCE": "ADVISOR_EVIDENCE_MISSING",
            "UNSUPPORTED": "ADVISOR_UNSUPPORTED",
            "SAFETY_REFUSAL": "ADVISOR_REFUSED",
            "INTERNAL_ERROR": "ADVISOR_INTERNAL",
        }
        if self.code != expected[self.status]:
            raise ValueError("Status/error code mismatch")
        citations = {c.id: c for c in self.citations}
        if len(citations) != len(self.citations):
            raise ValueError("Duplicate citation identity")
        for claim in self.claims:
            for key in claim.supporting_citation_ids + claim.context_citation_ids:
                citation = citations.get(key)
                if (
                    citation is None
                    or citation.entity_id != claim.entity_id
                    or citation.field != claim.field
                ):
                    raise ValueError("Citation does not apply to claim")
                if key in claim.supporting_citation_ids and (
                    citation.role != "supports_stored_field"
                    or citation.verification_status != "verified"
                ):
                    raise ValueError("Unverified citation cannot support a claim")
        return self
