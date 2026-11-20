"""Mémoire IA structurée persistante et clés d'idempotence IA.

Revision ID: 0011_ai_first_memory
Revises: 0010_personal_goals_planning
Create Date: 2026-11-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011_ai_first_memory"
down_revision: Union[str, Sequence[str], None] = "0010_personal_goals_planning"
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

    with op.batch_alter_table("ai_messages") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=80), nullable=True))
    op.create_index(
        "ix_ai_messages_idempotency",
        "ai_messages",
        ["user_id", "conversation_id", "idempotency_key"],
    )

    with op.batch_alter_table("ai_action_proposals") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=80), nullable=True))
        batch_op.create_unique_constraint(
            "uq_ai_action_proposals_user_idem",
            ["user_id", "idempotency_key"],
        )
    op.create_index(
        "ix_ai_action_proposals_idempotency",
        "ai_action_proposals",
        ["user_id", "idempotency_key"],
    )

    op.create_table(
        "user_ai_memory",
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("academic_context", json_type, nullable=False, server_default=json_obj_default),
        sa.Column(
            "availability_preferences",
            json_type,
            nullable=False,
            server_default=json_obj_default,
        ),
        sa.Column(
            "learning_preferences",
            json_type,
            nullable=False,
            server_default=json_obj_default,
        ),
        sa.Column("constraints", json_type, nullable=False, server_default=json_arr_default),
        sa.Column("long_term_goals", json_type, nullable=False, server_default=json_arr_default),
        sa.Column("recent_decisions", json_type, nullable=False, server_default=json_arr_default),
        sa.Column("execution_history", json_type, nullable=False, server_default=json_arr_default),
        sa.Column("weekly_study_hours", sa.Integer(), nullable=True),
        sa.Column(
            "default_session_minutes",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
        sa.Column(
            "auto_execute_simple_actions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "weekly_study_hours IS NULL OR (weekly_study_hours >= 0 AND weekly_study_hours <= 120)",
            name="ck_user_ai_memory_weekly_hours",
        ),
        sa.CheckConstraint(
            "default_session_minutes >= 15 AND default_session_minutes <= 240",
            name="ck_user_ai_memory_session_minutes",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_ai_memory")

    op.drop_index("ix_ai_action_proposals_idempotency", table_name="ai_action_proposals")
    with op.batch_alter_table("ai_action_proposals") as batch_op:
        batch_op.drop_constraint("uq_ai_action_proposals_user_idem", type_="unique")
        batch_op.drop_column("idempotency_key")

    op.drop_index("ix_ai_messages_idempotency", table_name="ai_messages")
    with op.batch_alter_table("ai_messages") as batch_op:
        batch_op.drop_column("idempotency_key")
