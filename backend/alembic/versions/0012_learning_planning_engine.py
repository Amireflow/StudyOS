"""Ajout du moteur de disponibilités et des versions du programme d'apprentissage

Revision ID: 0012_learning_planning_engine
Revises: 0011_ai_first_memory
Create Date: 2026-11-20 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_learning_planning_engine"
down_revision = "0011_ai_first_memory"
branch_labels = None
depends_on = None


def _json_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _json_server_default(bind, literal: str):
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{literal}'::jsonb")
    return sa.text(f"'{literal}'")


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "user_availability_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.String(length=5), nullable=True),
        sa.Column("end_time", sa.String(length=5), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Europe/Paris",
        ),
        sa.Column(
            "recurrence",
            sa.String(length=24),
            nullable=False,
            server_default="weekly",
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "rule_type IN ('personal_unavailability', 'confirmed_availability', 'recovery_time')",
            name="ck_user_availability_rules_type",
        ),
        sa.CheckConstraint(
            "recurrence IN ('once', 'weekly', 'daily')",
            name="ck_user_availability_rules_recurrence",
        ),
        sa.CheckConstraint(
            "day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)",
            name="ck_user_availability_rules_dow",
        ),
    )
    op.create_index(
        "ix_user_availability_rules_user_id",
        "user_availability_rules",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_availability_rules_active",
        "user_availability_rules",
        ["user_id", "active"],
        unique=False,
    )

    op.create_table(
        "learning_plan_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.String(length=24),
            nullable=False,
            server_default="proposed",
        ),
        sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Europe/Paris",
        ),
        sa.Column("idempotency_key", sa.String(length=80), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "plan_payload",
            _json_type(),
            nullable=False,
            server_default=_json_server_default(bind, "{}"),
        ),
        sa.Column(
            "applied_event_ids",
            _json_type(),
            nullable=False,
            server_default=_json_server_default(bind, "[]"),
        ),
        sa.Column(
            "applied_task_ids",
            _json_type(),
            nullable=False,
            server_default=_json_server_default(bind, "[]"),
        ),
        sa.Column(
            "applied_course_ids",
            _json_type(),
            nullable=False,
            server_default=_json_server_default(bind, "[]"),
        ),
        sa.Column(
            "replaced_event_snapshots",
            _json_type(),
            nullable=False,
            server_default=_json_server_default(bind, "[]"),
        ),
        sa.Column("parent_version_id", sa.Uuid(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["learning_plan_versions.id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'applied', 'rejected', 'superseded', 'restored')",
            name="ck_learning_plan_versions_status",
        ),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_learning_plan_versions_num",
        ),
        sa.CheckConstraint(
            "horizon_days >= 1 AND horizon_days <= 30",
            name="ck_learning_plan_versions_horizon",
        ),
        sa.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_learning_plan_versions_user_idem",
        ),
    )
    op.create_index(
        "ix_learning_plan_versions_user_id",
        "learning_plan_versions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_learning_plan_versions_status",
        "learning_plan_versions",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_learning_plan_versions_idem",
        "learning_plan_versions",
        ["user_id", "idempotency_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_learning_plan_versions_idem", table_name="learning_plan_versions")
    op.drop_index("ix_learning_plan_versions_status", table_name="learning_plan_versions")
    op.drop_index("ix_learning_plan_versions_user_id", table_name="learning_plan_versions")
    op.drop_table("learning_plan_versions")

    op.drop_index("ix_user_availability_rules_active", table_name="user_availability_rules")
    op.drop_index("ix_user_availability_rules_user_id", table_name="user_availability_rules")
    op.drop_table("user_availability_rules")
