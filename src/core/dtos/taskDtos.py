from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .userDtos import UserResponseDto
    from .subjectDtos import SubjectResponseDto
    from .facultyDtos import FacultyResponseDto
    from .departmentDtos import DepartmentResponseDto
    from .yearDtos import YearResponseDto
    from .attachmentDtos import AttachmentResponseDto

from core.dtos.baseDtos import BaseSearchDto


class TaskCreateDto(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=60, description="Title or name of the task"
    )
    url: str | None = Field(
        default=None,
        max_length=100,
        description="URL where the task should be submitted",
    )
    deadline: datetime = Field(..., description="Datetime for the task deadline")
    subject_id: int = Field(
        ..., gt=0, description="ID of the subject this task belongs to"
    )
    details: dict = Field(
        default_factory=dict,
        description="Additional details about the task (stored as JSON) (eg. urls, links, description)",
    )


class TaskResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the task")
    name: str | None = Field(default=None, description="Name/Title of the task")
    task_type: str | None = Field(
        default=None, description="Type of the entry (e.g., 'Exam', 'Task')"
    )
    url: str | None = Field(default=None, description="Submission URL for the task")
    details: dict | None = Field(
        default=None,
        description="Additional details about the task including description and files (eg. urls, links, description)",
    )
    deadline: datetime | None = Field(
        default=None, description="Deadline datetime of the task"
    )
    due_date: datetime | None = Field(default=None, description="Due date of the task")
    created_at: datetime | None = Field(
        default=None, description="Creation Date of the task"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last Update Date of the task"
    )

    # Relationships
    author: UserResponseDto | None = Field(
        default=None, description="User who created the task"
    )
    subject: SubjectResponseDto | None = Field(
        default=None, description="Subject associated with the task"
    )
    attachments: list[AttachmentResponseDto] | None = Field(
        default=None, description="List of attachments associated with the task"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class TaskUpdateDto(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=60,
        description="Title or name of the task",
    )
    url: str | None = Field(
        default=None,
        max_length=100,
        description="URL where the task should be submitted",
    )
    deadline: datetime = Field(..., description="Datetime for the task deadline")
    subject_id: int = Field(
        ..., gt=0, description="ID of the subject this task belongs to"
    )
    details: dict = Field(
        default_factory=dict, description="Additional details about the task (eg. urls, links, description)"
    )


class TaskDeleteDto(BaseModel):
    id: int = Field(..., description="ID of the task to delete")


class TaskSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the task to search for")
    subject_id: int | None = Field(
        default=None, description="ID of Subject to filter by"
    )
    faculty_id: int | None = Field(
        default=None, description="ID of Faculty to filter by"
    )
    department_id: int | None = Field(
        default=None, description="ID of Department to filter by"
    )
    year_id: int | None = Field(
        default=None, description="ID of Academic Year to filter by"
    )
    author_id: int | None = Field(default=None, description="ID of Author to filter by")
    deadline_from: str | None = Field(
        default=None, description="Start date to filter by (>=)"
    )
    deadline_to: str | None = Field(
        default=None, description="End date to filter by (<=)"
    )
    created_at_from: str | None = Field(
        default=None, description="Start date to filter by creation date (>=)"
    )
    created_at_to: str | None = Field(
        default=None, description="End date to filter by creation date (<=)"
    )
    updated_at_from: str | None = Field(
        default=None, description="Start date to filter by last update date (>=)"
    )
    updated_at_to: str | None = Field(
        default=None, description="End date to filter by last update date (<=)"
    )
