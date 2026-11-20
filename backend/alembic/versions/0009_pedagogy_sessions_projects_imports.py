"""Pédagogie v2 (sources IA, versions de niveau, tentatives), résultats de séance structurés, projets en pause et snapshot d'import.

Revision ID: 0009_pedagogy_sessions_projects
Revises: 0008_p0_security_integrity
Create Date: 2026-11-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_pedagogy_sessions_projects"
down_revision: Union[str, Sequence[str], None] = "0008_p0_security_integrity"
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
    bind = op.get_bind()

    # 1. courses
    op.add_column(
        "courses",
        sa.Column(
            "generation_source",
            sa.String(length=32),
            nullable=False,
            server_default="curated_local",
        ),
    )
    op.add_column(
        "courses",
        sa.Column("generation_model", sa.String(length=120), nullable=True),
    )

    # 2. course_levels
    op.add_column(
        "course_levels",
        sa.Column(
            "previous_versions",
            json_type,
            nullable=False,
            server_default=json_arr_default,
        ),
    )
    op.add_column(
        "course_levels",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "course_levels",
        sa.Column(
            "generation_source",
            sa.String(length=32),
            nullable=False,
            server_default="curated_local",
        ),
    )

    # 3. course_submissions
    op.add_column(
        "course_submissions",
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "course_submissions",
        sa.Column(
            "evaluation_mode",
            sa.String(length=32),
            nullable=False,
            server_default="deterministic",
        ),
    )
    op.add_column(
        "course_submissions",
        sa.Column(
            "manual_review_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "course_submissions",
        sa.Column("static_analysis", json_type, nullable=True),
    )

    # 4. study_sessions
    op.add_column(
        "study_sessions",
        sa.Column("outcome_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "study_sessions",
        sa.Column("deliverable_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "study_sessions",
        sa.Column("blockers", sa.Text(), nullable=True),
    )
    op.add_column(
        "study_sessions",
        sa.Column("next_step", sa.Text(), nullable=True),
    )

    # 5. timetable_imports
    op.add_column(
        "timetable_imports",
        sa.Column("replaced_snapshot", json_type, nullable=True),
    )

    # 6. projects : autoriser le statut 'paused'
    new_check = "status IN ('planned', 'active', 'paused', 'blocked', 'completed', 'archived')"
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS ck_projects_status")
        op.create_check_constraint("ck_projects_status", "projects", new_check)
    else:
        with op.batch_alter_table("projects") as batch_op:
            batch_op.drop_constraint("ck_projects_status", type_="check")
            batch_op.create_check_constraint("ck_projects_status", new_check)


def downgrade() -> None:
    bind = op.get_bind()
    old_check = "status IN ('planned', 'active', 'blocked', 'completed', 'archived')"
    op.execute("UPDATE projects SET status = 'planned' WHERE status = 'paused'")
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS ck_projects_status")
        op.create_check_constraint("ck_projects_status", "projects", old_check)
    else:
        with op.batch_alter_table("projects") as batch_op:
            batch_op.drop_constraint("ck_projects_status", type_="check")
            batch_op.create_check_constraint("ck_projects_status", old_check)

    op.drop_column("timetable_imports", "replaced_snapshot")

    op.drop_column("study_sessions", "next_step")
    op.drop_column("study_sessions", "blockers")
    op.drop_column("study_sessions", "deliverable_summary")
    op.drop_column("study_sessions", "outcome_status")

    op.drop_column("course_submissions", "static_analysis")
    op.drop_column("course_submissions", "manual_review_required")
    op.drop_column("course_submissions", "evaluation_mode")
    op.drop_column("course_submissions", "attempt_number")

    op.drop_column("course_levels", "generation_source")
    op.drop_column("course_levels", "revision")
    op.drop_column("course_levels", "previous_versions")

    op.drop_column("courses", "generation_model")
    op.drop_column("courses", "generation_source")
