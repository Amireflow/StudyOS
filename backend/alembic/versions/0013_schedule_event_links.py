"""Ajout des clés étrangères optionnelles sur schedule_events (objectif, cours, projet, tâche)

Revision ID: 0013_schedule_event_links
Revises: 0012_learning_planning_engine
Create Date: 2026-11-20 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_schedule_event_links"
down_revision = "0012_learning_planning_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("schedule_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("goal_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("course_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("project_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("task_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_schedule_events_goal_id",
            "personal_goals",
            ["goal_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_schedule_events_course_id",
            "courses",
            ["course_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_schedule_events_project_id",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_schedule_events_task_id",
            "tasks",
            ["task_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("schedule_events", schema=None) as batch_op:
        batch_op.drop_constraint("fk_schedule_events_task_id", type_="foreignkey")
        batch_op.drop_constraint("fk_schedule_events_project_id", type_="foreignkey")
        batch_op.drop_constraint("fk_schedule_events_course_id", type_="foreignkey")
        batch_op.drop_constraint("fk_schedule_events_goal_id", type_="foreignkey")
        batch_op.drop_column("task_id")
        batch_op.drop_column("project_id")
        batch_op.drop_column("course_id")
        batch_op.drop_column("goal_id")
