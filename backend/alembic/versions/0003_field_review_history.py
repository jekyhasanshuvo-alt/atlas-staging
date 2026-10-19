"""Append-only field review chains; preserve legacy attribution rows."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    table = "verification_records"
    op.add_column(table, sa.Column("review_field", sa.String(64)))
    op.add_column(table, sa.Column("value_fingerprint", sa.String(64)))
    op.add_column(table, sa.Column("supersedes_id", sa.String(80)))
    op.create_foreign_key(
        "fk_verification_records_supersedes_id_verification_records",
        table,
        table,
        ["supersedes_id"],
        ["id"],
    )
    op.create_unique_constraint("uq_verification_records_supersedes_id", table, ["supersedes_id"])
    for target in ("university", "program"):
        op.drop_constraint(f"uq_verification_records_source_id_{target}_id", table, type_="unique")
        op.create_index(
            f"uq_verification_{target}_attribution",
            table,
            ["source_id", f"{target}_id"],
            unique=True,
            postgresql_where=sa.text("review_field IS NULL"),
        )
        op.create_index(
            f"uq_verification_{target}_first_review",
            table,
            ["source_id", f"{target}_id", "review_field"],
            unique=True,
            postgresql_where=sa.text("review_field IS NOT NULL AND supersedes_id IS NULL"),
        )
    op.create_check_constraint(
        "field_decision",
        table,
        "(review_field IS NULL AND value_fingerprint IS NULL AND supersedes_id IS NULL) OR "
        "(review_field IS NOT NULL AND value_fingerprint IS NOT NULL AND "
        "length(value_fingerprint) = 64 AND reviewed_fields = review_field AND "
        "(university_id IS NOT NULL OR program_id IS NOT NULL) AND "
        "verification_status != 'unverified' AND reviewed_at IS NOT NULL AND "
        "reviewed_by IS NOT NULL AND length(trim(reviewed_by)) > 0)",
    )
    op.execute("""
        CREATE FUNCTION atlas_review_chain_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
               OR predecessor.reviewed_at > NEW.reviewed_at THEN
              RAISE EXCEPTION 'Invalid review predecessor' USING ERRCODE = '23514';
            END IF;
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER atlas_review_chain_guard BEFORE INSERT OR UPDATE OR DELETE
        ON verification_records FOR EACH ROW EXECUTE FUNCTION atlas_review_chain_guard();
    """)


def downgrade():
    # Never discard history silently or restore uniqueness over populated chains.
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM verification_records WHERE review_field IS NOT NULL) THEN
        RAISE EXCEPTION 'Preserve/export review history before downgrade';
      END IF;
    END $$;""")
    op.execute("DROP TRIGGER atlas_review_chain_guard ON verification_records")
    op.execute("DROP FUNCTION atlas_review_chain_guard()")
    table = "verification_records"
    op.drop_constraint(op.f("ck_verification_records_field_decision"), table, type_="check")
    for target in ("university", "program"):
        op.drop_index(f"uq_verification_{target}_first_review", table_name=table)
        op.drop_index(f"uq_verification_{target}_attribution", table_name=table)
        op.create_unique_constraint(
            f"uq_verification_records_source_id_{target}_id", table, ["source_id", f"{target}_id"]
        )
    op.drop_constraint("uq_verification_records_supersedes_id", table, type_="unique")
    op.drop_constraint(
        "fk_verification_records_supersedes_id_verification_records", table, type_="foreignkey"
    )
    for column in ("supersedes_id", "value_fingerprint", "review_field"):
        op.drop_column(table, column)
