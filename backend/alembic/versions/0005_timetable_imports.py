"""Import intelligent de l'emploi du temps : table timetable_imports et métadonnées de cours sur schedule_events.

Revision ID: 0005_timetable_imports
Revises: 0004_skill_assessments_pedagogical_lock
Create Date: 2026-11-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_timetable_imports"
down_revision: Union[str, Sequence[str], None] = "0004_skill_assessments_pedagogical_lock"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "timetable_imports",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_format", sa.String(length=20), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_preview_text", sa.Text(), nullable=True),
        sa.Column("source_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending_review"),
        sa.Column("valid_from", sa.String(length=10), nullable=True),
        sa.Column("valid_until", sa.String(length=10), nullable=True),
        sa.Column("extracted_courses", json_type, nullable=False),
        sa.Column("anomalies", json_type, nullable=False),
        sa.Column("warnings", json_type, nullable=False),
        sa.Column("created_events_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_duplicates_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("replaced_events_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending_review', 'validated', 'cancelled')",
            name="ck_timetable_imports_status",
        ),
        sa.CheckConstraint(
            "file_format IN ('pdf', 'image', 'excel', 'word')",
            name="ck_timetable_imports_format",
        ),
        sa.CheckConstraint(
            "file_size_bytes > 0",
            name="ck_timetable_imports_size",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_timetable_imports_user_id", "timetable_imports", ["user_id"])
    op.create_index("ix_timetable_imports_status", "timetable_imports", ["status"])
    op.create_index("ix_timetable_imports_created_at", "timetable_imports", ["created_at"])

    op.add_column(
        "schedule_events",
        sa.Column("source", sa.String(length=30), nullable=False, server_default="manual"),
    )
    op.add_column(
        "schedule_events",
        sa.Column("import_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "schedule_events",
        sa.Column("session_subtype", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "schedule_events",
        sa.Column("teacher", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "schedule_events",
        sa.Column("room", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "schedule_events",
        sa.Column("group_name", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_schedule_import_id", "schedule_events", ["import_id"])


def downgrade() -> None:
    op.drop_index("ix_schedule_import_id", table_name="schedule_events")
    op.drop_column("schedule_events", "group_name")
    op.drop_column("schedule_events", "room")
    op.drop_column("schedule_events", "teacher")
    op.drop_column("schedule_events", "session_subtype")
    op.drop_column("schedule_events", "import_id")
    op.drop_column("schedule_events", "source")

    op.drop_index("ix_timetable_imports_created_at", table_name="timetable_imports")
    op.drop_index("ix_timetable_imports_status", table_name="timetable_imports")
    op.drop_index("ix_timetable_imports_user_id", table_name="timetable_imports")
    op.drop_table("timetable_imports")
