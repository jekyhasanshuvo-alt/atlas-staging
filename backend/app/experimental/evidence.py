"""Read-only synthetic diagnostics; never a review decision or eligibility evaluator."""

import hashlib
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select

from app.experimental import models as m
from app.experimental.schemas import AdmissionsFacts
from app.models.catalog import AcademicProgram, DataSource, VerificationRecord
from app.services.review import canonical, current_records, fingerprint, source_ready


def leaf_paths(value, prefix=""):
    if isinstance(value, dict):
        if value.get("state") in {"unknown", "not_applicable"}:
            return set()
        return set().union(
            *(
                leaf_paths(v, prefix + "/" + str(k).replace("~", "~0").replace("/", "~1"))
                for k, v in value.items()
                if k not in {"gaps", "state", "reason"}
            )
        )
    if isinstance(value, list):
        return set().union(*(leaf_paths(v, prefix + "/" + str(i)) for i, v in enumerate(value)))
    return {prefix} if value is not None else set()


def resolve(payload, path):
    node = payload
    for segment in path.split("/")[1:]:
        segment = segment.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            if not segment.isdigit() or str(int(segment)) != segment:
                raise ValueError("Invalid array pointer")
            node = node[int(segment)]
        else:
            node = node[segment]
    return node


def context_digest(version, intake, evidence, capture, source):
    return fingerprint(
        {
            "namespace": "atlas.fact-context.v1",
            "version_id": str(version.id),
            "targets": [version.program_id, version.scholarship_id, version.university_id],
            "intake": [str(intake.id), intake.program_id, intake.cycle_key, intake.round_key],
            "payload": version.payload,
            "content_sha256": version.content_sha256,
            "evidence": [
                str(evidence.id),
                evidence.field_path,
                resolve(version.payload, evidence.field_path),
                evidence.locator,
                evidence.excerpt,
            ],
            "capture": [
                str(capture.id),
                capture.source_id,
                capture.metadata,
                capture.content_sha256,
                capture.captured_at,
            ],
            "source": [
                source.id,
                source.source_type,
                source.title,
                source.source_url,
                source.publisher,
                source.retrieved_at,
            ],
        }
    )


def diagnose(db, version_id, capture_bytes, at=None):
    at = at or datetime.now(UTC)
    issues = []
    version = db.get(m.CatalogFactVersion, version_id)
    if not version or version.topic != "admissions":
        return {
            "status": "NOT_ASSESSED",
            "issues": ["missing_admissions_version"],
            "coverage_complete": False,
        }
    if db.scalar(
        select(m.CatalogFactVersion.id).where(m.CatalogFactVersion.predecessor_id == version.id)
    ):
        issues.append("superseded_version")
    intake = db.get(m.ProgramIntake, version.intake_id)
    program = db.get(AcademicProgram, version.program_id)
    try:
        facts = AdmissionsFacts.model_validate(version.payload)
        if (
            intake.program_id != version.program_id
            or facts.intake.country_id != program.university.country_id
            or facts.intake.degree != program.degree_level
        ):
            issues.append("scope_mismatch")
        if (
            facts.intake.academic_cycle.state != "known"
            or facts.intake.academic_cycle.value != intake.cycle_key
        ):
            issues.append("cycle_unknown_or_mismatch")
        if facts.intake.year.state != "known" or facts.intake.term.state != "known":
            issues.append("intake_unknown")
    except (ValidationError, AttributeError):
        issues.append("unsupported_or_invalid_payload")
    # Uses existing canonical serialization, under an explicit new namespace.
    if version.content_sha256 != fingerprint(version.payload):
        issues.append("payload_digest_mismatch")
    evidence_rows = list(
        db.scalars(select(m.FactFieldEvidence).where(m.FactFieldEvidence.version_id == version.id))
    )
    paths = leaf_paths(version.payload)
    coverage = paths <= {e.field_path for e in evidence_rows}
    if not coverage:
        issues.append("incomplete_exact_field_coverage")
    for evidence in evidence_rows:
        try:
            if (
                evidence.field_path not in paths
                or resolve(version.payload, evidence.field_path) is None
            ):
                issues.append("invalid_evidence_path")
                continue
        except (KeyError, IndexError, TypeError, ValueError):
            issues.append("invalid_evidence_path")
            continue
        capture = db.get(m.OfficialSourceCapture, evidence.capture_id)
        source = db.get(DataSource, evidence.source_id)
        if capture is None or source is None or capture.source_id != evidence.source_id:
            issues.append("capture_source_mismatch")
            continue
        raw = capture_bytes.get(capture.id)
        if raw is None or hashlib.sha256(raw).hexdigest() != capture.content_sha256:
            issues.append("capture_custody_unavailable_or_mismatch")
        if (
            capture.captured_at > at
            or source.source_type != "official"
            or not source_ready(source, at)
        ):
            issues.append("source_unready")
        expected = {
            "source_url": source.source_url,
            "title": source.title,
            "publisher": source.publisher,
            "source_type": source.source_type,
            "retrieved_at": source.retrieved_at,
        }
        if any(capture.metadata.get(k) != canonical(v) for k, v in expected.items()):
            issues.append("source_metadata_changed_or_superseded")
        if any(
            capture.metadata.get(k) != v
            for k, v in {
                "program_id": version.program_id,
                "cycle_key": intake.cycle_key,
                "round_key": intake.round_key,
            }.items()
        ):
            issues.append("capture_scope_mismatch")
        expected_hash = context_digest(version, intake, evidence, capture, source)
        records = list(
            db.scalars(
                select(VerificationRecord).where(
                    VerificationRecord.source_id == source.id,
                    VerificationRecord.review_field == "fact:" + str(evidence.id),
                )
            )
        )
        heads = current_records(records)
        if len(heads) != 1:
            issues.append("missing_or_ambiguous_review")
            continue
        head = heads[0]
        bound = db.scalar(
            select(m.FactReviewBinding.review_id).where(
                m.FactReviewBinding.evidence_id == evidence.id,
                m.FactReviewBinding.version_id == version.id,
                m.FactReviewBinding.review_id == head.id,
            )
        )
        if (
            not bound
            or head.value_fingerprint != expected_hash
            or head.verification_status != "verified"
            or head.program_id != version.program_id
            or head.reviewed_at > at
            or head.valid_from
            and head.valid_from > at
            or head.valid_until
            and head.valid_until < at
        ):
            issues.append("stale_unverified_or_unbound_review")
    return {
        "status": "NOT_ASSESSED",
        "issues": sorted(set(issues)),
        "coverage_complete": coverage,
        "activation_blocker": "New review semantics and capture custody are not approved; diagnostics never authorize claims.",
    }
