"""Palier 2 Lot 6 schema: learning_paths, learning_modules, lessons, skills, skill_evidence, projects.

Revision ID: 0002_palier2_learning_skills_projects
Revises: 0001_initial_palier1
Create Date: 2026-11-19
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_palier2_learning_skills_projects"
down_revision: Union[str, Sequence[str], None] = "0001_initial_palier1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "learning_paths",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("goal", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('not_started', 'active', 'paused', 'completed')",
            name="ck_learning_paths_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_paths_user_id", "learning_paths", ["user_id"])
    op.create_index("ix_learning_paths_status", "learning_paths", ["status"])

    op.create_table(
        "learning_modules",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("path_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_learning_modules_position"),
        sa.CheckConstraint(
            "status IN ('not_started', 'active', 'paused', 'completed')",
            name="ck_learning_modules_status",
        ),
        sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_modules_user_id", "learning_modules", ["user_id"])
    op.create_index("ix_learning_modules_path_id", "learning_modules", ["path_id"])

    op.create_table(
        "lessons",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("module_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("resource_url", sa.String(length=500), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_lessons_position"),
        sa.CheckConstraint(
            "status IN ('not_started', 'active', 'paused', 'completed')",
            name="ck_lessons_status",
        ),
        sa.ForeignKeyConstraint(["module_id"], ["learning_modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lessons_user_id", "lessons", ["user_id"])
    op.create_index("ix_lessons_module_id", "lessons", ["module_id"])

    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("domain", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_level", sa.Integer(), nullable=False),
        sa.Column("target_level", sa.Integer(), nullable=True),
        sa.Column("last_assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("current_level >= 0 AND current_level <= 5", name="ck_skills_current_level"),
        sa.CheckConstraint(
            "target_level IS NULL OR (target_level >= 0 AND target_level <= 5)",
            name="ck_skills_target_level",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skills_user_id", "skills", ["user_id"])
    op.create_index("ix_skills_domain", "skills", ["domain"])

    op.create_table(
        "skill_evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("skill_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reference_url", sa.String(length=500), nullable=True),
        sa.Column("result", sa.String(length=200), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "type IN ('exercise', 'project', 'code', 'assessment', 'deliverable', 'other')",
            name="ck_skill_evidence_type",
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skill_evidence_user_id", "skill_evidence", ["user_id"])
    op.create_index("ix_skill_evidence_skill_id", "skill_evidence", ["skill_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("goal", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("next_action", sa.String(length=240), nullable=False),
        sa.Column("deliverables", json_type, nullable=True),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned', 'active', 'blocked', 'completed', 'archived')",
            name="ck_projects_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name="ck_projects_priority",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])
    op.create_index("ix_projects_status", "projects", ["status"])


def downgrade() -> None:
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_skill_evidence_skill_id", table_name="skill_evidence")
    op.drop_index("ix_skill_evidence_user_id", table_name="skill_evidence")
    op.drop_table("skill_evidence")

    op.drop_index("ix_skills_domain", table_name="skills")
    op.drop_index("ix_skills_user_id", table_name="skills")
    op.drop_table("skills")

    op.drop_index("ix_lessons_module_id", table_name="lessons")
    op.drop_index("ix_lessons_user_id", table_name="lessons")
    op.drop_table("lessons")

    op.drop_index("ix_learning_modules_path_id", table_name="learning_modules")
    op.drop_index("ix_learning_modules_user_id", table_name="learning_modules")
    op.drop_table("learning_modules")

    op.drop_index("ix_learning_paths_status", table_name="learning_paths")
    op.drop_index("ix_learning_paths_user_id", table_name="learning_paths")
    op.drop_table("learning_paths")
