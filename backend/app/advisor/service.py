import hashlib
import re
from datetime import UTC, datetime

from app.advisor.provider import OfflineProvider, enforce
from app.advisor.schemas import Answer, Citation, Claim
from app.services.financial_scenario import calculate
from app.services.intelligence import public_url

LIMITATIONS = [
    "Offline deterministic templates, not LLM reasoning. Stored Atlas snapshots only; no live pages fetched.",
    "Preference matches, self-reports, personal stages and hypothetical costs are not verified admissions, awards or financial sufficiency.",
    "No chat history is stored or sent to external providers. Official current-intake requirements and deadlines remain unknown.",
]
UNSAFE = re.compile(
    r"(?i)(ignore.{0,30}(rules|instructions|system)|system\s*prompt|developer\s*message|jailbreak|other.{0,15}(student|user|account)|(?:execute|run)\s+(?:sql|shell|code|command)|\b(?:curl|wget|drop table|pg_sleep)\b|mark.{0,35}(?:verified|eligible)|fabricat.{0,20}(?:citation|source)|(?:send|post|upload|exfiltrat).{0,40}(?:data|profile|secret|http)|(?:change|update|alter).{0,30}(?:stage|application|database)|(?:guarantee|guaranteed).{0,25}(?:admission|award|scholarship)|(?:https?://|file:|data:|blob:|www\.))"
)
FIELDS = {
    "university": [
        "name",
        "institution_type",
        "official_website",
        "intake",
        "admission_requirements",
    ],
    "program": [
        "name",
        "degree_level",
        "field_of_study",
        "language_of_instruction",
        "duration_months",
        "tuition_amount",
        "tuition_currency",
        "tuition_period",
        "intake",
        "admission_requirements",
    ],
    "scholarship": ["name", "provider", "description", "eligibility_summary", "coverage"],
}


def classify(question):
    q = question.casefold()
    if re.search(
        r"\b(eligib|admiss|acceptance|probability|deadline|nationality|bangladesh|document requirement)",
        q,
    ):
        return "eligibility"
    for intent, pattern in [
        ("financial", r"budget|financial|cost|afford"),
        ("matching", r"match|preference"),
        ("compare", r"compar"),
        ("scholarship", r"scholarship|funding"),
        ("program", r"program|programme|course"),
        ("university", r"universit|college"),
        ("planning", r"application|personal stage|prepare|planning|next step"),
    ]:
        if re.search(pattern, q):
            return intent
    return "unsupported"


def clean(value, limit=240):
    text = str(value)
    if len(text) > limit or UNSAFE.search(text) or any(ord(c) < 32 for c in text):
        return None
    return text


def answer(status, code, intent, summary, **kwargs):
    return Answer(
        status=status,
        code=code,
        intent=intent,
        scope=kwargs.pop("scope", "general"),
        summary=summary,
        limitations=LIMITATIONS,
        **kwargs,
    )


def citations(record, field, fact, now):
    results = []
    for evidence in fact.evidence[:1]:
        source = evidence.source
        if (
            evidence.evidence_reference != f"{source.id}:{field}"
            or not clean(source.title)
            or not clean(source.publisher)
        ):
            continue
        retrieved = source.retrieved_at
        reviewed = evidence.reviewed_at
        support = (
            not record.is_demo
            and fact.verification_status == "verified"
            and evidence.verification_status == "verified"
            and source.source_type in {"official_university", "official_government"}
            and retrieved is not None
            and reviewed is not None
            and retrieved.tzinfo is not None
            and reviewed.tzinfo is not None
            and retrieved <= now
            and reviewed <= now
            and reviewed >= retrieved
        )
        context = hashlib.sha256(
            f"{record.kind}:{record.id}:{field}:{fact.value}:{fact.verification_status}:{evidence.verification_status}:{reviewed}:{source.model_dump_json()}".encode()
        ).hexdigest()
        key = context[:24]
        results.append(
            Citation(
                id=key,
                review_context=context,
                entity_id=record.id,
                entity_kind=record.kind,
                field=field,
                source_id=source.id,
                source_title=source.title,
                source_url=public_url(source.source_url),
                publisher=source.publisher,
                source_type=source.source_type,
                retrieved_at=retrieved,
                reviewed_at=reviewed,
                verification_status=evidence.verification_status,
                role="supports_stored_field" if support else "context_only",
                freshness="stored_snapshot_current_review" if support else "not_current_support",
            )
        )
    return results


def compose(data, retriever, provider=None, now=None):
    intent = classify(data.question) if data.intent == "auto" else data.intent
    if (
        UNSAFE.search(data.question)
        or UNSAFE.search(data.search)
        or (
            data.preferences
            and any(UNSAFE.search(str(v)) for v in data.preferences.model_dump().values())
        )
    ):
        return answer(
            "SAFETY_REFUSAL",
            "ADVISOR_REFUSED",
            intent,
            "This advisor cannot execute instructions, disclose account data, fabricate evidence or guarantee outcomes.",
        )
    if intent == "eligibility" or classify(data.question) == "eligibility":
        prepared = answer(
            "INSUFFICIENT_EVIDENCE",
            "ADVISOR_EVIDENCE_MISSING",
            "eligibility",
            "Eligibility is NOT_ASSESSED. Exact current program/intake/nationality rules and independently approved evidence are missing.",
            unknowns=[
                "Official eligibility",
                "Applicable intake",
                "Official deadline",
                "Official document requirements",
                "Bangladesh-specific applicability",
            ],
        )
    elif intent == "unsupported":
        prepared = answer(
            "UNSUPPORTED",
            "ADVISOR_UNSUPPORTED",
            intent,
            "This offline advisor supports catalog explanations, explicit preferences, hypothetical scenarios and general application planning.",
            follow_ups=[
                "Explain why eligibility is not assessed",
                "Suggest personal application planning steps",
            ],
        )
    elif intent == "planning":
        claims = [
            Claim(
                id="general-plan",
                text="Record your own shortlist, identify official program/intake contacts, confirm requirements directly, and maintain personal preparation tasks.",
                basis="general_guidance",
            )
        ]
        if data.personal_stage:
            claims.append(
                Claim(
                    id="personal-stage",
                    text=f"Your supplied personal stage is {data.personal_stage}; no institution receipt, offer or admission is confirmed.",
                    basis="user_managed_stage",
                    value=data.personal_stage,
                )
            )
        prepared = answer(
            "SUPPORTED",
            "ADVISOR_OK",
            intent,
            "General personal planning guidance only; operational journey persistence remains disabled.",
            scope="request_scoped" if data.personal_stage else "general",
            claims=claims,
            unknowns=["Official requirements", "Official deadlines"],
        )
    elif intent == "financial":
        if data.scenario is None:
            prepared = answer(
                "INSUFFICIENT_EVIDENCE",
                "ADVISOR_EVIDENCE_MISSING",
                intent,
                "Supply an explicit hypothetical scenario to reuse the existing Financial Twin calculator.",
                unknowns=["Explicit scenario inputs"],
            )
        else:
            result = calculate(data.scenario)
            prepared = answer(
                "SUPPORTED" if result.status == "complete" else "INSUFFICIENT_EVIDENCE",
                "ADVISOR_OK" if result.status == "complete" else "ADVISOR_EVIDENCE_MISSING",
                intent,
                "Existing Financial Twin formulas reused exactly. No award, exchange rate, affordability or missing cost is inferred.",
                scope="request_scoped",
                scenario_result=result,
                unknowns=result.missing_inputs,
                claims=[
                    Claim(id=f"formula-{i}", text=line, basis="hypothetical_scenario")
                    for i, line in enumerate(result.formulas)
                ],
            )
    else:
        kind = (
            "scholarship"
            if intent == "scholarship"
            else "university"
            if intent == "university"
            else "program"
        )
        rows = retriever.retrieve(kind, data.entity_ids, data.search)
        if len(rows) > 4:
            raise ValueError("Retriever exceeded bounded result count")
        claims = []
        refs = []
        unknowns = []
        for record in rows:
            if record.kind != kind or (data.entity_ids and record.id not in data.entity_ids):
                raise ValueError("Retriever scope mismatch")
            for field in FIELDS[kind]:
                fact = record.facts.get(field)
                value = (
                    clean(fact.value, 1000 if kind == "scholarship" else 240)
                    if fact and fact.value is not None
                    else None
                )
                if value is None or value == "":
                    unknowns.append(f"{record.id}:{field} unknown or unsafe text withheld")
                    continue
                entries = citations(record, field, fact, now or datetime.now(UTC))
                refs.extend(entries)
                supported = [c.id for c in entries if c.role == "supports_stored_field"]
                claims.append(
                    Claim(
                        id=f"{record.id}:{field}",
                        entity_id=record.id,
                        field=field,
                        value=value,
                        text=f"Stored {field}: {value}"
                        + (" (demo; not factually verified)" if record.is_demo else ""),
                        basis="supported_stored_field" if supported else "stored_catalog",
                        verification_status=fact.verification_status
                        if not record.is_demo
                        else "unverified",
                        supporting_citation_ids=supported,
                        context_citation_ids=[c.id for c in entries if c.role == "context_only"],
                    )
                )
            if intent == "matching":
                if not data.preferences:
                    unknowns.append("Explicit request preferences not supplied")
                else:
                    for attribute, field in [
                        ("degree", "degree_level"),
                        ("subject", "field_of_study"),
                        ("language", "language_of_instruction"),
                    ]:
                        requested = getattr(data.preferences, attribute)
                        fact = record.facts.get(field)
                        if requested is None:
                            continue
                        actual = clean(fact.value) if fact and fact.value is not None else None
                        same = (
                            actual is not None
                            and " ".join(requested.split()).casefold()
                            == " ".join(actual.split()).casefold()
                        )
                        claims.append(
                            Claim(
                                id=f"{record.id}:preference:{attribute}",
                                text=f"Explicit {attribute} preference: "
                                + ("UNKNOWN" if actual is None else "MATCH" if same else "DIFFERS")
                                + ". Exact stored-value comparison only; admissions NOT_ASSESSED.",
                                basis="explicit_user_preference",
                            )
                        )
        refs = list({c.id: c for c in refs}.values())
        unavailable = [key for key in data.entity_ids if key not in {r.id for r in rows}]
        status = "PARTIALLY_SUPPORTED" if claims else "INSUFFICIENT_EVIDENCE"
        if claims and not unknowns and all(c.basis == "supported_stored_field" for c in claims):
            status = "SUPPORTED"
        prepared = answer(
            status,
            {
                "SUPPORTED": "ADVISOR_OK",
                "PARTIALLY_SUPPORTED": "ADVISOR_PARTIAL",
                "INSUFFICIENT_EVIDENCE": "ADVISOR_EVIDENCE_MISSING",
            }[status],
            intent,
            "Stored catalog fields with exact provenance; original currency and tuition period remain separate. No intake applicability or eligibility is inferred."
            if claims
            else "No usable released catalog evidence matched. Legacy scholarship descriptions and blocked pilots are not official requirements.",
            scope="selected_catalog",
            claims=claims,
            citations=refs,
            unknowns=unknowns + (["Some selected IDs are unavailable"] if unavailable else []),
            unavailable_ids=unavailable,
            follow_ups=[
                "Explain why eligibility is not assessed",
                "Suggest personal application planning steps",
            ],
        )
    return enforce(prepared, provider or OfflineProvider())
