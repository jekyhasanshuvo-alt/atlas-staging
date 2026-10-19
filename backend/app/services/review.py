"""Trusted local operator workflow. Callers own the outer transaction."""

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import (
    AcademicProgram,
    DataSource,
    Scholarship,
    University,
    VerificationRecord,
)
from app.schemas.curated import PROGRAM_FIELDS, UNIVERSITY_FIELDS, safe_url
from app.schemas.scholarship import field_value, term_document, valid_path

DECISIONS = ("under_review", "verified", "rejected", "stale")
TARGETS = {
    "university": (University, UNIVERSITY_FIELDS),
    "program": (AcademicProgram, PROGRAM_FIELDS),
    "scholarship": (Scholarship, None),
}


def allowed_path(kind, field):
    return kind in TARGETS and (
        valid_path(field) if kind == "scholarship" else field in TARGETS[kind][1]
    )


def value_for(entity, field):
    return field_value(entity, field) if isinstance(entity, Scholarship) else getattr(entity, field)


def value_fingerprint(entity, source, field):
    if not isinstance(entity, Scholarship):
        # Preserve the exact historical university/program fingerprint payload.
        return fingerprint({field: getattr(entity, field)})
    terms = term_document(entity).model_dump(mode="json")
    terms["scopes"] = sorted(terms["scopes"], key=lambda scope: scope["id"])
    return fingerprint(
        {
            "scholarship_fingerprint_version": 1,
            "value": {field: value_for(entity, field)},
            "terms": terms,
            "identity": [entity.id, entity.name, entity.provider, entity.official_url],
            "legacy": [
                entity.funding_type,
                entity.funding_amount,
                entity.funding_currency,
                entity.coverage,
                entity.eligibility_summary,
                entity.application_deadline,
            ],
            "source": [
                source.source_type,
                source.source_url,
                source.publisher,
                source.retrieved_at,
            ],
        }
    )


def canonical(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite value")
        return {"decimal": format(value.normalize(), "f") if value else "0"}
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Timezone required")
        return {"datetime": value.astimezone(UTC).isoformat()}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError("Unsupported value type")


def fingerprint(value):
    payload = json.dumps(
        canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_ready(source, now):
    try:
        return bool(
            source
            and source.source_type != "demo"
            and source.source_url
            and safe_url(source.source_url)
            and source.publisher.strip()
            and source.retrieved_at
            and source.retrieved_at <= now
        )
    except ValueError:
        return False


def attributed_fields(record):
    if record.review_field is not None:
        return set()
    try:
        data = json.loads(record.notes)
        fields = data.get("attributed_fields")
        if (
            data.get("schema_version") == 1
            and isinstance(fields, list)
            and all(isinstance(f, str) for f in fields)
        ):
            return set(fields)
    except (ValueError, AttributeError, TypeError):
        pass
    return set()


def current_records(records):
    superseded = {r.supersedes_id for r in records if r.supersedes_id}
    return [r for r in records if r.id not in superseded]


def field_supported(entity, source, field, records, now):
    kind = (
        "scholarship"
        if isinstance(entity, Scholarship)
        else "university"
        if isinstance(entity, University)
        else "program"
    )
    try:
        value = value_for(entity, field) if allowed_path(kind, field) else None
    except ValueError:
        return False
    return bool(
        not entity.is_demo
        and source_ready(source, now)
        and allowed_path(kind, field)
        and value is not None
        and any(r.source_id == source.id and field in attributed_fields(r) for r in records)
    )


def context(session, kind, identifier, source_id, field, *, lock=False):
    if not allowed_path(kind, field):
        raise ValueError("Unsupported entity or field")
    model = TARGETS[kind][0]
    query = select(model).where(model.id == identifier).execution_options(populate_existing=True)
    entity = session.scalar(query.with_for_update() if lock else query)
    if entity is None:
        raise ValueError("Entity does not exist")
    if isinstance(entity, Scholarship):
        session.expire(entity, ["scopes"])
    source = session.get(DataSource, source_id)
    records = list(
        session.scalars(
            select(VerificationRecord).where(
                getattr(VerificationRecord, kind + "_id") == identifier
            )
        )
    )
    if not field_supported(entity, source, field, records, datetime.now(UTC)):
        raise ValueError(
            "Non-demo entity, known attributed field and valid source metadata required"
        )
    heads = [
        r for r in current_records(records) if r.source_id == source_id and r.review_field == field
    ]
    if len(heads) > 1:
        raise ValueError("Ambiguous review history")
    head = heads[0] if heads else None
    value_hash = value_fingerprint(entity, source, field)
    token = fingerprint(
        {
            "kind": kind,
            "entity": identifier,
            "source": source_id,
            "field": field,
            "head": head.id if head else None,
            "value": value_hash,
            "source_metadata": [
                source.source_type,
                source.source_url,
                source.publisher,
                source.retrieved_at,
            ],
            "attribution": sorted(
                r.notes for r in records if r.source_id == source_id and r.review_field is None
            ),
        }
    )
    return entity, head, value_hash, token


def preview(session, kind, identifier, source_id, field):
    with session.no_autoflush:
        entity, head, value_hash, token = context(session, kind, identifier, source_id, field)
        return {
            "entity_type": kind,
            "entity_id": identifier,
            "source_id": source_id,
            "field": field,
            "value": canonical(value_for(entity, field)),
            "predecessor": head.id if head else None,
            "value_fingerprint": value_hash,
            "token": token,
            "reviewed_at": datetime.now(UTC).isoformat(),
        }


def decide(
    session: Session,
    kind,
    identifier,
    source_id,
    field,
    *,
    status,
    token,
    reviewer,
    operator,
    reviewed_at,
    valid_until=None,
    confirmed=False,
    supports_value=False,
):
    if not operator.strip() or reviewer != operator or not reviewer.strip() or len(reviewer) > 200:
        raise ValueError("Reviewer must match the explicitly configured local operator")
    if not confirmed or status not in DECISIONS:
        raise ValueError("Explicit confirmation and supported decision required")
    now = datetime.now(UTC)
    if reviewed_at.tzinfo is None or reviewed_at > now:
        raise ValueError("Review time must be timezone-aware and not in the future")
    if valid_until is not None and (
        valid_until.tzinfo is None or valid_until <= now or valid_until < reviewed_at
    ):
        raise ValueError("Validity must be timezone-aware and not expired")
    if status == "verified" and not supports_value:
        raise ValueError("Confirm the source supports the exact previewed value")
    request = {
        "kind": kind,
        "entity": identifier,
        "source": source_id,
        "field": field,
        "status": status,
        "token": token,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "valid_until": valid_until,
        "supports_value": supports_value,
    }
    decision_id = "review-" + fingerprint(request)
    if session.new or session.dirty or session.deleted:
        raise ValueError("Use a clean session dedicated to review")
    with session.begin_nested():
        entity, head, value_hash, expected = context(
            session, kind, identifier, source_id, field, lock=True
        )
        existing = session.get(VerificationRecord, decision_id)
        if existing is not None:
            return existing
        if token != expected:
            raise ValueError("Stale preview; preview again before submitting")
        if valid_until is not None and valid_until <= datetime.now(UTC):
            raise ValueError("Validity expired while waiting for the review lock")
        source = session.get(DataSource, source_id)
        if reviewed_at < source.retrieved_at or (head and reviewed_at < head.reviewed_at):
            raise ValueError("Review cannot predate source retrieval or predecessor")
        record = VerificationRecord(
            id=decision_id,
            **{kind + "_id": entity.id},
            source_id=source_id,
            review_field=field,
            reviewed_fields=field,
            value_fingerprint=value_hash,
            supersedes_id=head.id if head else None,
            verification_status=status,
            reviewed_by=reviewer,
            reviewed_at=reviewed_at,
            valid_from=reviewed_at,
            valid_until=valid_until,
            notes="",
        )
        session.add(record)
        session.flush()
        # Refresh already-loaded collections without introducing serializer queries.
        session.expire(entity, ["verifications"])
        return record


def history(session, kind, identifier, source_id, field):
    if not allowed_path(kind, field):
        raise ValueError("Unsupported entity or field")
    records = list(
        session.scalars(
            select(VerificationRecord)
            .where(
                getattr(VerificationRecord, kind + "_id") == identifier,
                VerificationRecord.source_id == source_id,
                VerificationRecord.review_field == field,
            )
            .order_by(VerificationRecord.reviewed_at, VerificationRecord.id)
        )
    )
    heads = {r.id for r in current_records(records)}
    return [
        {
            "id": r.id,
            "predecessor": r.supersedes_id,
            "current": r.id in heads,
            "status": r.verification_status,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at.isoformat(),
            "value_fingerprint": r.value_fingerprint,
            "valid_until": r.valid_until.isoformat() if r.valid_until else None,
        }
        for r in records
    ]
