"""Nullable scholarship terms, destination scopes and independent field review."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

FIELDS = {
    "scheme_key": sa.String(120),
    "round_key": sa.String(80),
    "intake_label": sa.String(120),
    "academic_cycle": sa.String(40),
    "intake_start_date": sa.Date(),
    "cycle_state": sa.String(20),
    "provider_kind": sa.String(20),
    "applicability_state": sa.String(20),
    "benefits": JSONB(none_as_null=True),
    "requirements": JSONB(none_as_null=True),
    "deadlines": JSONB(none_as_null=True),
}
CHECKS = {
    "contract_version": "contract_version IN (1,2) AND (contract_version != 1 OR funding_type IS NOT NULL)",
    "cycle_state": "cycle_state IS NULL OR cycle_state IN ('known','unknown')",
    "applicability_state": "applicability_state IS NULL OR applicability_state IN ('unknown','listed','unrestricted')",
    "provider_kind": "provider_kind IS NULL OR provider_kind IN ('government','university','foundation','other','unknown')",
    "structured_identity": "contract_version != 2 OR (scheme_key IS NOT NULL AND round_key IS NOT NULL AND cycle_state IS NOT NULL AND applicability_state IS NOT NULL)",
    **{
        f"{key}_object": f"{key} IS NULL OR jsonb_typeof({key}) = 'object'"
        for key in ("benefits", "requirements", "deadlines")
    },
}


def field_check(scholarship):
    targets = "university_id IS NOT NULL OR program_id IS NOT NULL"
    if scholarship:
        targets += " OR scholarship_id IS NOT NULL"
    return (
        "(review_field IS NULL AND value_fingerprint IS NULL AND supersedes_id IS NULL) OR "
        "(review_field IS NOT NULL AND value_fingerprint IS NOT NULL AND "
        "length(value_fingerprint) = 64 AND reviewed_fields = review_field AND "
        f"({targets}) AND verification_status != 'unverified' AND reviewed_at IS NOT NULL AND "
        "reviewed_by IS NOT NULL AND length(trim(reviewed_by)) > 0)"
    )


def chain_guard(scholarship):
    extra = (
        "OR predecessor.scholarship_id IS DISTINCT FROM NEW.scholarship_id" if scholarship else ""
    )
    op.execute(f"""
    CREATE OR REPLACE FUNCTION atlas_review_chain_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE predecessor verification_records%ROWTYPE;
    BEGIN
      IF TG_OP = 'DELETE' THEN
        IF OLD.review_field IS NOT NULL THEN
          RAISE EXCEPTION 'Review decisions are immutable' USING ERRCODE = '23514';
        END IF;
        RETURN OLD;
      END IF;
      IF TG_OP = 'UPDATE' THEN
        IF OLD.review_field IS NOT NULL OR NEW.review_field IS NOT NULL THEN
          RAISE EXCEPTION 'Review decisions are immutable' USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.supersedes_id IS NOT NULL THEN
        SELECT * INTO predecessor FROM verification_records WHERE id = NEW.supersedes_id;
        IF NOT FOUND OR predecessor.review_field IS NULL
           OR predecessor.review_field IS DISTINCT FROM NEW.review_field
           OR predecessor.source_id IS DISTINCT FROM NEW.source_id
           OR predecessor.university_id IS DISTINCT FROM NEW.university_id
           OR predecessor.program_id IS DISTINCT FROM NEW.program_id
           {extra}
           OR predecessor.reviewed_at > NEW.reviewed_at THEN
          RAISE EXCEPTION 'Invalid review predecessor' USING ERRCODE = '23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    """)


def upgrade():
    op.add_column(
        "scholarships",
        sa.Column("contract_version", sa.Integer(), nullable=False, server_default="1"),
    )
    for name, type_ in FIELDS.items():
        op.add_column("scholarships", sa.Column(name, type_, nullable=True))
    op.alter_column("scholarships", "funding_type", nullable=True)
    for name, condition in CHECKS.items():
        op.create_check_constraint(name, "scholarships", condition)
    op.create_unique_constraint(
        "uq_scholarships_scheme_key_round_key", "scholarships", ["scheme_key", "round_key"]
    )
    op.create_index("ix_scholarships_scheme_key", "scholarships", ["scheme_key"])
    op.create_table(
        "scholarship_scopes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "scholarship_id",
            sa.String(36),
            sa.ForeignKey("scholarships.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("country_id", sa.String(36), sa.ForeignKey("countries.id", ondelete="RESTRICT")),
        sa.Column(
            "university_id", sa.String(36), sa.ForeignKey("universities.id", ondelete="RESTRICT")
        ),
        sa.Column(
            "program_id", sa.String(36), sa.ForeignKey("academic_programs.id", ondelete="RESTRICT")
        ),
        sa.Column("degree_level", sa.String(20)),
        sa.Column("scope_extent", sa.String(20), nullable=False, server_default="exact_target"),
        sa.CheckConstraint(
            "num_nonnulls(country_id, university_id, program_id) = 1", name="exactly_one_target"
        ),
        sa.CheckConstraint(
            "degree_level IS NULL OR degree_level IN ('Bachelor','Master','PhD')", name="degree"
        ),
        sa.CheckConstraint(
            "scope_extent IN ('exact_target','descendants') AND (program_id IS NULL OR scope_extent = 'exact_target')",
            name="scope_extent",
        ),
    )
    for column in ("scholarship_id", "country_id", "university_id", "program_id"):
        op.create_index(f"ix_scholarship_scopes_{column}", "scholarship_scopes", [column])
    for target in ("country", "university", "program"):
        op.create_index(
            f"uq_scholarship_scope_{target}",
            "scholarship_scopes",
            [
                "scholarship_id",
                f"{target}_id",
                sa.text("coalesce(degree_level, '')"),
                "scope_extent",
            ],
            unique=True,
            postgresql_where=sa.text(f"{target}_id IS NOT NULL"),
        )
    table = "verification_records"
    op.drop_constraint("uq_verification_records_source_id_scholarship_id", table, type_="unique")
    op.create_index(
        "uq_verification_scholarship_attribution",
        table,
        ["source_id", "scholarship_id"],
        unique=True,
        postgresql_where=sa.text("review_field IS NULL"),
    )
    op.create_index(
        "uq_verification_scholarship_first_review",
        table,
        ["source_id", "scholarship_id", "review_field"],
        unique=True,
        postgresql_where=sa.text("review_field IS NOT NULL AND supersedes_id IS NULL"),
    )
    op.drop_constraint(op.f("ck_verification_records_field_decision"), table, type_="check")
    op.create_check_constraint("field_decision", table, field_check(True))
    chain_guard(True)


def downgrade():
    populated = " OR ".join(f"{name} IS NOT NULL" for name in FIELDS)
    op.execute(f"""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM scholarships WHERE contract_version != 1 OR {populated})
         OR EXISTS (SELECT 1 FROM scholarship_scopes)
         OR EXISTS (SELECT 1 FROM verification_records WHERE scholarship_id IS NOT NULL AND review_field IS NOT NULL) THEN
        RAISE EXCEPTION 'Preserve/export scholarship terms and review history before downgrade';
      END IF;
    END $$;""")
    chain_guard(False)
    table = "verification_records"
    op.drop_constraint(op.f("ck_verification_records_field_decision"), table, type_="check")
    op.create_check_constraint("field_decision", table, field_check(False))
    op.drop_index("uq_verification_scholarship_first_review", table_name=table)
    op.drop_index("uq_verification_scholarship_attribution", table_name=table)
    op.create_unique_constraint(
        "uq_verification_records_source_id_scholarship_id", table, ["source_id", "scholarship_id"]
    )
    op.drop_table("scholarship_scopes")
    op.drop_index("ix_scholarships_scheme_key", table_name="scholarships")
    op.drop_constraint("uq_scholarships_scheme_key_round_key", "scholarships", type_="unique")
    for name in CHECKS:
        op.drop_constraint(op.f(f"ck_scholarships_{name}"), "scholarships", type_="check")
    for name in FIELDS:
        op.drop_column("scholarships", name)
    op.drop_column("scholarships", "contract_version")
    op.alter_column("scholarships", "funding_type", nullable=False)
