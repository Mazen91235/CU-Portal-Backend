"""Updated Type Name

Revision ID: e3f3fcb807c4
Revises: 5d19c37050e9
Create Date: 2026-08-21 06:50:23.113686

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e3f3fcb807c4"
down_revision: Union[str, Sequence[str], None] = "5d19c37050e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename columns to preserve existing data
    op.alter_column("materials", "type", new_column_name="material_type")
    op.alter_column("notifications", "type", new_column_name="notification_type")
    op.alter_column("tokens", "type", new_column_name="token_type")
    op.alter_column("users", "type", new_column_name="study_type")

    # Rename tasks column and update affected indexes
    op.alter_column("tasks", "type", new_column_name="task_type")
    op.drop_index(
        op.f("idx_task_type_faculty_department_year_name"), table_name="tasks"
    )
    op.create_index(
        "idx_task_task_type_faculty_department_year_name",
        "tasks",
        ["task_type", "faculty_id", "department_id", "year_id", "name"],
        unique=False,
    )
    op.drop_index(
        op.f("idx_task_type_faculty_department_year_subject_due_date_name"),
        table_name="tasks",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert index names back to using 'type'
    op.create_index(
        op.f("idx_task_type_faculty_department_year_subject_due_date_name"),
        "tasks",
        [
            "type",
            "faculty_id",
            "department_id",
            "year_id",
            "subject_id",
            "due_date",
            "name",
        ],
        unique=False,
    )
    op.drop_index("idx_task_task_type_faculty_department_year_name", table_name="tasks")
    op.create_index(
        op.f("idx_task_type_faculty_department_year_name"),
        "tasks",
        ["type", "faculty_id", "department_id", "year_id", "name"],
        unique=False,
    )

    # Revert column names back
    op.alter_column("tasks", "task_type", new_column_name="type")
    op.alter_column("users", "study_type", new_column_name="type")
    op.alter_column("tokens", "token_type", new_column_name="type")
    op.alter_column("notifications", "notification_type", new_column_name="type")
    op.alter_column("materials", "material_type", new_column_name="type")
