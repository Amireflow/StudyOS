"""Verrou pédagogique : table skill_assessments pour la validation traçable des compétences.

Revision ID: 0004_skill_assessments_pedagogical_lock
Revises: 0003_palier2_ai_copilot
Create Date: 2026-11-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_skill_assessments_pedagogical_lock"
down_revision: Union[str, Sequence[str], None] = "0003_palier2_ai_copilot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "skill_assessments",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("skill_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("path_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("module_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("lesson_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("assessment_type", sa.String(length=30), nullable=False),
        sa.Column("starting_level", sa.Integer(), nullable=False),
        sa.Column("target_level", sa.Integer(), nullable=False),
        sa.Column("proposed_level", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("prompt_title", sa.String(length=180), nullable=False),
        sa.Column("prompt_instructions", sa.Text(), nullable=False),
        sa.Column("hints", json_type, nullable=False),
        sa.Column("hints_revealed_count", sa.Integer(), nullable=False),
        sa.Column("submission_text", sa.Text(), nullable=True),
        sa.Column("submission_code", sa.Text(), nullable=True),
        sa.Column("submission_reference_url", sa.String(length=500), nullable=True),
        sa.Column("evidence_ids", json_type, nullable=False),
        sa.Column("criteria", json_type, nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("mastered_points", json_type, nullable=False),
        sa.Column("gaps_identified", json_type, nullable=False),
        sa.Column("remediation_recommendation", sa.Text(), nullable=True),
        sa.Column("external_verification_warning", sa.Text(), nullable=True),
        sa.Column("evaluator_type", sa.String(length=30), nullable=False),
        sa.Column("evaluator_name", sa.String(length=80), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("applied_level_delta", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "starting_level >= 0 AND starting_level <= 5",
            name="ck_skill_assessments_starting_level",
        ),
        sa.CheckConstraint(
            "target_level >= 1 AND target_level <= 5",
            name="ck_skill_assessments_target_level",
        ),
        sa.CheckConstraint(
            "proposed_level IS NULL OR (proposed_level >= 0 AND proposed_level <= 5)",
            name="ck_skill_assessments_proposed_level",
        ),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_skill_assessments_score",
        ),
        sa.CheckConstraint(
            "hints_revealed_count >= 0",
            name="ck_skill_assessments_hints_revealed",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'submitted', 'evaluated', 'approved', 'rejected', 'cancelled')",
            name="ck_skill_assessments_status",
        ),
        sa.CheckConstraint(
            "assessment_type IN ('quiz', 'practical_exercise', 'code_review', 'explanation', 'deliverable', 'mixed')",
            name="ck_skill_assessments_type",
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["module_id"], ["learning_modules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skill_assessments_user_id", "skill_assessments", ["user_id"])
    op.create_index("ix_skill_assessments_skill_id", "skill_assessments", ["skill_id"])
    op.create_index("ix_skill_assessments_status", "skill_assessments", ["status"])
    op.create_index(
        "ix_skill_assessments_user_skill",
        "skill_assessments",
        ["user_id", "skill_id"],
    )
    op.create_index("ix_skill_assessments_path_id", "skill_assessments", ["path_id"])
    op.create_index("ix_skill_assessments_module_id", "skill_assessments", ["module_id"])
    op.create_index("ix_skill_assessments_lesson_id", "skill_assessments", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_skill_assessments_lesson_id", table_name="skill_assessments")
    op.drop_index("ix_skill_assessments_module_id", table_name="skill_assessments")
    op.drop_index("ix_skill_assessments_path_id", table_name="skill_assessments")
    op.drop_index("ix_skill_assessments_user_skill", table_name="skill_assessments")
    op.drop_index("ix_skill_assessments_status", table_name="skill_assessments")
    op.drop_index("ix_skill_assessments_skill_id", table_name="skill_assessments")
    op.drop_index("ix_skill_assessments_user_id", table_name="skill_assessments")
    op.drop_table("skill_assessments")
