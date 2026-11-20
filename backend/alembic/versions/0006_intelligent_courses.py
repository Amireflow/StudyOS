"""Module Cours intelligent : courses, course_levels, course_lessons, course_resources, course_submissions.

Revision ID: 0006_intelligent_courses
Revises: 0005_timetable_imports
Create Date: 2026-11-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_intelligent_courses"
down_revision: Union[str, Sequence[str], None] = "0005_timetable_imports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("domain", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="fr"),
        sa.Column("current_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_levels", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("language IN ('fr', 'en', 'bilingual')", name="ck_courses_language"),
        sa.CheckConstraint(
            "current_level >= 1 AND current_level <= 5",
            name="ck_courses_current_level",
        ),
        sa.CheckConstraint(
            "total_levels >= 1 AND total_levels <= 5",
            name="ck_courses_total_levels",
        ),
        sa.CheckConstraint("current_level <= total_levels", name="ck_courses_level_bounds"),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'completed')",
            name="ck_courses_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_courses_user_id", "courses", ["user_id"])
    op.create_index("ix_courses_status", "courses", ["status"])
    op.create_index("ix_courses_skill_id", "courses", ["skill_id"])

    op.create_table(
        "course_levels",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "course_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("objectives", json_type, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="locked"),
        sa.Column(
            "content_generated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("project_title", sa.String(length=180), nullable=True),
        sa.Column("project_brief", sa.Text(), nullable=True),
        sa.Column("project_deliverables", json_type, nullable=False),
        sa.Column("project_rubric", json_type, nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "level_number >= 1 AND level_number <= 5",
            name="ck_course_levels_number",
        ),
        sa.CheckConstraint(
            "status IN ('locked', 'unlocked', 'in_progress', 'validated')",
            name="ck_course_levels_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_levels_user_id", "course_levels", ["user_id"])
    op.create_index("ix_course_levels_course_id", "course_levels", ["course_id"])
    op.create_index("ix_course_levels_course_num", "course_levels", ["course_id", "level_number"])

    op.create_table(
        "course_lessons",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "course_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "level_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("course_levels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=300), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("code_examples", json_type, nullable=False),
        sa.Column("exercises", json_type, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="not_started"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 1", name="ck_course_lessons_position"),
        sa.CheckConstraint(
            "estimated_minutes >= 5 AND estimated_minutes <= 240",
            name="ck_course_lessons_minutes",
        ),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="ck_course_lessons_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_lessons_user_id", "course_lessons", ["user_id"])
    op.create_index("ix_course_lessons_course_id", "course_lessons", ["course_id"])
    op.create_index("ix_course_lessons_level_id", "course_lessons", ["level_id"])

    op.create_table(
        "course_resources",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "course_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "level_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("course_levels.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "lesson_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("course_lessons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="fr"),
        sa.Column(
            "is_official",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("source_name", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "resource_type IN ('documentation', 'video', 'article', 'book', 'interactive')",
            name="ck_course_resources_type",
        ),
        sa.CheckConstraint("language IN ('fr', 'en')", name="ck_course_resources_language"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_resources_user_id", "course_resources", ["user_id"])
    op.create_index("ix_course_resources_course_id", "course_resources", ["course_id"])
    op.create_index("ix_course_resources_level_id", "course_resources", ["level_id"])

    op.create_table(
        "course_submissions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "course_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "level_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("course_levels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lesson_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("course_lessons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("submission_kind", sa.String(length=20), nullable=False),
        sa.Column("exercise_id", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("submitted_code", sa.Text(), nullable=True),
        sa.Column("reference_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="evaluated"),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("criteria_results", json_type, nullable=False),
        sa.Column("feedback_markdown", sa.Text(), nullable=True),
        sa.Column("strengths", json_type, nullable=False),
        sa.Column("improvements", json_type, nullable=False),
        sa.Column("next_step_hint", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "submission_kind IN ('exercise', 'project')",
            name="ck_course_submissions_kind",
        ),
        sa.CheckConstraint(
            "status IN ('submitted', 'evaluated')",
            name="ck_course_submissions_status",
        ),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_course_submissions_score",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_submissions_user_id", "course_submissions", ["user_id"])
    op.create_index("ix_course_submissions_course_id", "course_submissions", ["course_id"])
    op.create_index("ix_course_submissions_level_id", "course_submissions", ["level_id"])


def downgrade() -> None:
    op.drop_index("ix_course_submissions_level_id", table_name="course_submissions")
    op.drop_index("ix_course_submissions_course_id", table_name="course_submissions")
    op.drop_index("ix_course_submissions_user_id", table_name="course_submissions")
    op.drop_table("course_submissions")

    op.drop_index("ix_course_resources_level_id", table_name="course_resources")
    op.drop_index("ix_course_resources_course_id", table_name="course_resources")
    op.drop_index("ix_course_resources_user_id", table_name="course_resources")
    op.drop_table("course_resources")

    op.drop_index("ix_course_lessons_level_id", table_name="course_lessons")
    op.drop_index("ix_course_lessons_course_id", table_name="course_lessons")
    op.drop_index("ix_course_lessons_user_id", table_name="course_lessons")
    op.drop_table("course_lessons")

    op.drop_index("ix_course_levels_course_num", table_name="course_levels")
    op.drop_index("ix_course_levels_course_id", table_name="course_levels")
    op.drop_index("ix_course_levels_user_id", table_name="course_levels")
    op.drop_table("course_levels")

    op.drop_index("ix_courses_skill_id", table_name="courses")
    op.drop_index("ix_courses_status", table_name="courses")
    op.drop_index("ix_courses_user_id", table_name="courses")
    op.drop_table("courses")
