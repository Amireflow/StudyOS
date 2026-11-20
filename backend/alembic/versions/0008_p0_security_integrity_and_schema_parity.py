"""Sécurité P0, intégrité pédagogique, chiffrement clés IA, sessions & parité schéma.

Revision ID: 0008_p0_security_integrity
Revises: 0007_user_accounts_auth
Create Date: 2026-11-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_p0_security_integrity"
down_revision: Union[str, Sequence[str], None] = "0007_user_accounts_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _json_server_default(empty_literal: str) -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{empty_literal}'::jsonb")
    return sa.text(f"'{empty_literal}'")


def upgrade() -> None:
    json_obj_default = _json_server_default("{}")
    json_arr_default = _json_server_default("[]")

    # 1. Nouvelles tables sécurité backend-only
    op.create_table(
        "user_ai_provider_configs",
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False, server_default="local"),
        sa.Column("base_url", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("api_key_last4", sa.String(length=8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "auth_refresh_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_refresh_sessions_user_id", "auth_refresh_sessions", ["user_id"])
    op.create_index("ix_auth_refresh_sessions_expires_at", "auth_refresh_sessions", ["expires_at"])
    op.create_index(
        "ix_auth_refresh_sessions_token_hash",
        "auth_refresh_sessions",
        ["token_hash"],
        unique=True,
    )

    op.create_table(
        "auth_login_attempts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False),
        sa.Column("account_key_hash", sa.String(length=64), nullable=True),
        sa.Column("client_ip_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "succeeded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope IN ('login', 'register', 'change_password', 'models_probe')",
            name="ck_auth_login_attempts_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auth_login_attempts_scope_account_ts",
        "auth_login_attempts",
        ["scope", "account_key_hash", "attempted_at"],
    )
    op.create_index(
        "ix_auth_login_attempts_scope_ip_ts",
        "auth_login_attempts",
        ["scope", "client_ip_hash", "attempted_at"],
    )

    op.create_table(
        "auth_token_revocations",
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("revoked_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # 2. Extension users
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "email_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch_op.add_column(
            sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True)
        )

    # 3. Extension skill_evidence (états de preuve + verrouillage)
    with op.batch_alter_table("skill_evidence") as batch_op:
        batch_op.add_column(
            sa.Column(
                "verification_status",
                sa.String(length=30),
                nullable=False,
                server_default="declared",
            )
        )
        batch_op.add_column(
            sa.Column(
                "inspection_metadata",
                json_type,
                nullable=False,
                server_default=json_obj_default,
            )
        )
        batch_op.add_column(
            sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_locked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch_op.create_check_constraint(
            "ck_skill_evidence_verification_status",
            "verification_status IN ('declared', 'uploaded', 'inspected', 'verified', 'approved', 'unreachable', 'rejected')",
        )

    # 4. Extension skill_assessments (versioning rubric + snapshots + manual_review)
    with op.batch_alter_table("skill_assessments") as batch_op:
        batch_op.drop_constraint("ck_skill_assessments_status", type_="check")
        batch_op.add_column(
            sa.Column(
                "rubric_version",
                sa.String(length=32),
                nullable=False,
                server_default="rubric-v2",
            )
        )
        batch_op.add_column(
            sa.Column(
                "evaluator_version",
                sa.String(length=32),
                nullable=False,
                server_default="eval-v2",
            )
        )
        batch_op.add_column(
            sa.Column(
                "evaluation_mode",
                sa.String(length=30),
                nullable=False,
                server_default="automated",
            )
        )
        batch_op.add_column(
            sa.Column(
                "manual_review_required",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "rubric_snapshot",
                json_type,
                nullable=False,
                server_default=json_arr_default,
            )
        )
        batch_op.add_column(
            sa.Column(
                "evidence_snapshot",
                json_type,
                nullable=False,
                server_default=json_arr_default,
            )
        )
        batch_op.add_column(
            sa.Column("reviewed_by", sa.String(length=120), nullable=True)
        )
        batch_op.create_check_constraint(
            "ck_skill_assessments_status",
            "status IN ('pending', 'submitted', 'evaluated', 'needs_manual_review', 'approved', 'rejected', 'cancelled')",
        )
        batch_op.create_check_constraint(
            "ck_skill_assessments_eval_mode",
            "evaluation_mode IN ('automated', 'ai_assisted', 'manual_review')",
        )

    # 5. Parité schéma : FK schedule_events.import_id, index FK & contrainte unique course_levels
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_fks = inspector.get_foreign_keys("schedule_events")
    has_import_fk = any(
        fk.get("referred_table") == "timetable_imports"
        and fk.get("constrained_columns") == ["import_id"]
        for fk in existing_fks
    )
    if not has_import_fk:
        with op.batch_alter_table("schedule_events") as batch_op:
            batch_op.create_foreign_key(
                "fk_schedule_events_import_id",
                "timetable_imports",
                ["import_id"],
                ["id"],
                ondelete="SET NULL",
            )

    existing_sessions_indexes = {idx["name"] for idx in inspector.get_indexes("study_sessions")}
    if "ix_sessions_task_id" not in existing_sessions_indexes:
        op.create_index("ix_sessions_task_id", "study_sessions", ["task_id"])

    existing_courses_indexes = {idx["name"] for idx in inspector.get_indexes("courses")}
    if "ix_courses_learning_path_id" not in existing_courses_indexes:
        op.create_index("ix_courses_learning_path_id", "courses", ["learning_path_id"])

    existing_res_indexes = {idx["name"] for idx in inspector.get_indexes("course_resources")}
    if "ix_course_resources_lesson_id" not in existing_res_indexes:
        op.create_index("ix_course_resources_lesson_id", "course_resources", ["lesson_id"])

    existing_sub_indexes = {idx["name"] for idx in inspector.get_indexes("course_submissions")}
    if "ix_course_submissions_lesson_id" not in existing_sub_indexes:
        op.create_index("ix_course_submissions_lesson_id", "course_submissions", ["lesson_id"])

    existing_level_uqs = {uq["name"] for uq in inspector.get_unique_constraints("course_levels")}
    if "uq_course_levels_course_num" not in existing_level_uqs:
        with op.batch_alter_table("course_levels") as batch_op:
            batch_op.create_unique_constraint(
                "uq_course_levels_course_num",
                ["course_id", "level_number"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_level_uqs = {uq["name"] for uq in inspector.get_unique_constraints("course_levels")}
    if "uq_course_levels_course_num" in existing_level_uqs:
        with op.batch_alter_table("course_levels") as batch_op:
            batch_op.drop_constraint("uq_course_levels_course_num", type_="unique")

    for table_name, idx_name in (
        ("course_submissions", "ix_course_submissions_lesson_id"),
        ("course_resources", "ix_course_resources_lesson_id"),
        ("courses", "ix_courses_learning_path_id"),
        ("study_sessions", "ix_sessions_task_id"),
    ):
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name=table_name)

    existing_fks = {fk.get("name") for fk in inspector.get_foreign_keys("schedule_events")}
    if "fk_schedule_events_import_id" in existing_fks:
        with op.batch_alter_table("schedule_events") as batch_op:
            batch_op.drop_constraint("fk_schedule_events_import_id", type_="foreignkey")

    with op.batch_alter_table("skill_assessments") as batch_op:
        batch_op.drop_constraint("ck_skill_assessments_eval_mode", type_="check")
        batch_op.drop_constraint("ck_skill_assessments_status", type_="check")
        batch_op.drop_column("reviewed_by")
        batch_op.drop_column("evidence_snapshot")
        batch_op.drop_column("rubric_snapshot")
        batch_op.drop_column("manual_review_required")
        batch_op.drop_column("evaluation_mode")
        batch_op.drop_column("evaluator_version")
        batch_op.drop_column("rubric_version")
        batch_op.create_check_constraint(
            "ck_skill_assessments_status",
            "status IN ('pending', 'submitted', 'evaluated', 'approved', 'rejected', 'cancelled')",
        )

    with op.batch_alter_table("skill_evidence") as batch_op:
        batch_op.drop_constraint("ck_skill_evidence_verification_status", type_="check")
        batch_op.drop_column("is_locked")
        batch_op.drop_column("inspected_at")
        batch_op.drop_column("inspection_metadata")
        batch_op.drop_column("verification_status")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("email_verified_at")
        batch_op.drop_column("email_verified")

    op.drop_table("auth_token_revocations")
    op.drop_index("ix_auth_login_attempts_scope_ip_ts", table_name="auth_login_attempts")
    op.drop_index("ix_auth_login_attempts_scope_account_ts", table_name="auth_login_attempts")
    op.drop_table("auth_login_attempts")
    op.drop_index("ix_auth_refresh_sessions_token_hash", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_expires_at", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_user_id", table_name="auth_refresh_sessions")
    op.drop_table("auth_refresh_sessions")
    op.drop_table("user_ai_provider_configs")
