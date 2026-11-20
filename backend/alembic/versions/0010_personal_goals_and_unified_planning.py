"""Objectifs personnels hors emploi du temps, enrichissement projets et suivi de séance.

Revision ID: 0010_personal_goals_planning
Revises: 0009_pedagogy_sessions_projects
Create Date: 2026-11-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010_personal_goals_planning"
down_revision: Union[str, Sequence[str], None] = "0009_pedagogy_sessions_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _json_server_default(empty_literal: str) -> sa.TextClause:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text(f"'{empty_literal}'::jsonb")
    return sa.text(f"'{empty_literal}'")


def upgrade() -> None:
    json_arr_default = _json_server_default("[]")

    op.create_table(
        "personal_goals",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "category",
            sa.String(length=40),
            nullable=False,
            server_default="learning_goal",
        ),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("goal", sa.String(length=300), nullable=False),
        sa.Column("current_level", sa.Integer(), nullable=True),
        sa.Column("target_level", sa.Integer(), nullable=True),
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=False,
            server_default="normal",
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("motivation", sa.Text(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "weekly_target_minutes",
            sa.Integer(),
            nullable=False,
            server_default="120",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("steps", json_type, nullable=False, server_default=json_arr_default),
        sa.Column("deliverables", json_type, nullable=False, server_default=json_arr_default),
        sa.Column("next_action", sa.String(length=240), nullable=False, server_default=""),
        sa.Column(
            "success_criteria",
            json_type,
            nullable=False,
            server_default=json_arr_default,
        ),
        sa.Column(
            "progress_history",
            json_type,
            nullable=False,
            server_default=json_arr_default,
        ),
        sa.Column(
            "skill_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "learning_path_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("learning_paths.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "course_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned', 'active', 'paused', 'blocked', 'completed', 'archived')",
            name="ck_personal_goals_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name="ck_personal_goals_priority",
        ),
        sa.CheckConstraint(
            "current_level IS NULL OR (current_level >= 0 AND current_level <= 5)",
            name="ck_personal_goals_current_level",
        ),
        sa.CheckConstraint(
            "target_level IS NULL OR (target_level >= 1 AND target_level <= 5)",
            name="ck_personal_goals_target_level",
        ),
        sa.CheckConstraint(
            "weekly_target_minutes >= 0",
            name="ck_personal_goals_weekly_minutes",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_personal_goals_user_id", "personal_goals", ["user_id"])
    op.create_index("ix_personal_goals_status", "personal_goals", ["status"])
    op.create_index("ix_personal_goals_skill_id", "personal_goals", ["skill_id"])
    op.create_index("ix_personal_goals_path_id", "personal_goals", ["learning_path_id"])
    op.create_index("ix_personal_goals_course_id", "personal_goals", ["course_id"])

    # Enrichissement projects
    op.add_column(
        "projects",
        sa.Column(
            "category",
            sa.String(length=40),
            nullable=False,
            server_default="project",
        ),
    )
    op.add_column("projects", sa.Column("motivation", sa.Text(), nullable=True))
    op.add_column(
        "projects",
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column(
            "weekly_target_minutes",
            sa.Integer(),
            nullable=False,
            server_default="180",
        ),
    )
    op.add_column(
        "projects",
        sa.Column("steps", json_type, nullable=False, server_default=json_arr_default),
    )
    op.add_column(
        "projects",
        sa.Column(
            "success_criteria",
            json_type,
            nullable=False,
            server_default=json_arr_default,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "progress_history",
            json_type,
            nullable=False,
            server_default=json_arr_default,
        ),
    )

    # Enrichissement study_sessions (Section 8)
    op.add_column(
        "study_sessions",
        sa.Column("planned_activity", sa.String(length=240), nullable=True),
    )
    op.add_column(
        "study_sessions",
        sa.Column("actual_activity", sa.Text(), nullable=True),
    )
    op.add_column(
        "study_sessions",
        sa.Column("goal_id", sa.Uuid(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("study_sessions", "goal_id")
    op.drop_column("study_sessions", "actual_activity")
    op.drop_column("study_sessions", "planned_activity")

    op.drop_column("projects", "progress_history")
    op.drop_column("projects", "success_criteria")
    op.drop_column("projects", "steps")
    op.drop_column("projects", "weekly_target_minutes")
    op.drop_column("projects", "start_date")
    op.drop_column("projects", "motivation")
    op.drop_column("projects", "category")

    op.drop_index("ix_personal_goals_course_id", table_name="personal_goals")
    op.drop_index("ix_personal_goals_path_id", table_name="personal_goals")
    op.drop_index("ix_personal_goals_skill_id", table_name="personal_goals")
    op.drop_index("ix_personal_goals_status", table_name="personal_goals")
    op.drop_index("ix_personal_goals_user_id", table_name="personal_goals")
    op.drop_table("personal_goals")
