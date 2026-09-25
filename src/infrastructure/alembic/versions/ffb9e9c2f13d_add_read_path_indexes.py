"""Add indexes for high-frequency read paths.

Revision ID: ffb9e9c2f13d
Revises: fa6fac071207
Create Date: 2026-09-25
"""
from typing import Sequence, Union

from alembic import op


revision: str = "ffb9e9c2f13d"
down_revision: Union[str, Sequence[str], None] = "fa6fac071207"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_user_notification_user_seen_id",
        "user_notifications",
        ["user_id", "seen", "id"],
        unique=False,
    )
    op.create_index(
        "idx_task_type_subject_id_deadline",
        "tasks",
        ["task_type", "subject_id", "deadline"],
        unique=False,
    )
    op.create_index(
        "idx_announcement_subject_id_date",
        "announcements",
        ["subject_id", "date"],
        unique=False,
    )
    op.create_index(
        "idx_event_faculty_department_year_start_date",
        "events",
        ["faculty_id", "department_id", "year_id", "start_date"],
        unique=False,
    )
    op.create_index(
        "idx_note_author_id_date",
        "notes",
        ["author_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_note_author_id_date", table_name="notes")
    op.drop_index("idx_event_faculty_department_year_start_date", table_name="events")
    op.drop_index("idx_announcement_subject_id_date", table_name="announcements")
    op.drop_index("idx_task_type_subject_id_deadline", table_name="tasks")
    op.drop_index("idx_user_notification_user_seen_id", table_name="user_notifications")
