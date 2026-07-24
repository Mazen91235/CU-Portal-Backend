from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .baseDtos import BaseSearchDto
    from .userDtos import UserResponseDto
    from .subjectDtos import SubjectResponseDto
    from .facultyDtos import FacultyResponseDto
    from .departmentDtos import DepartmentResponseDto
    from .yearDtos import YearResponseDto


class TaskLinkDto(BaseModel):
    url: str = Field(..., description="The URL of the external link")


class TaskCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=60, description="Title or name of the task")
    type: str | None = Field(
        default=None, max_length=10, description="Type of the entry (e.g., 'Exam', 'Assignment', 'Task')"
    )
    url: str | None = Field(
        default=None, max_length=100, description="URL where the task should be submitted"
    )
    urls: list[str] = Field(
        default_factory=list, description="List of Google Drive file URLs"
    )
    links: list[TaskLinkDto] = Field(
        default_factory=list, description="List of external links objects"
    )
    details: dict | None = Field(
        default=None, description="Additional details about the task (stored as JSON)"
    )
    deadline: datetime = Field(
        ..., description="Datetime for the task deadline"
    )
    due_date: datetime | None = Field(
        default=None, description="Datetime for the task due date (day only)"
    )
    subject_id: int = Field(
        ..., gt=0, description="ID of the subject this task belongs to"
    )
    
    author_id: int | None = Field(
        default=None, gt=0, description="ID of the author"
    )
    department_id: int | None = Field(
        default=None, gt=0, description="ID of the department this task belongs to"
    )
    faculty_id: int | None = Field(
        default=None, description="ID of the faculty this task belongs to"
    )
    year_id: int | None = Field(
        default=None, description="ID of the year this task belongs to"
    )


class TaskResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the task")
    name: str | None = Field(None, description="Name/Title of the task")
    type: str | None = Field(None, description="Type of the entry (e.g., 'Exam', 'Task')")
    url: str | None = Field(None, description="Submission URL for the task")
    urls: list[str] | None = Field(
        default=None, description="List of file URLs"
    )
    links: list[dict] | None = Field(
        default=None, description="List of external links"
    )
    details: dict | None = Field(
        None, description="Additional details about the task including description and files"
    )
    deadline: datetime | None = Field(None, description="Deadline datetime of the task")
    due_date: datetime | None = Field(None, description="Due date of the task")
    
    # Foreign Keys
    subject_id: int | None = Field(None, description="Subject ID associated with the task")
    author_id: int | None = Field(None, description="Author User ID who created the task")
    faculty_id: int | None = Field(None, description="Faculty ID associated with the task")
    department_id: int | None = Field(None, description="Department ID associated with the task")
    year_id: int | None = Field(None, description="Year ID associated with the task")
    
    modified_at: datetime | None = Field(None, description="Last Update Date of the task")

    # Relationships
    author: UserResponseDto | None = Field(
        None, description="User who created the task"
    )
    subject: SubjectResponseDto | None = Field(
        None, description="Subject associated with the task"
    )
    faculty: FacultyResponseDto | None = Field(
        None, description="Faculty associated with the task"
    )
    department: DepartmentResponseDto | None = Field(
        None, description="Department associated with the task"
    )
    year: YearResponseDto | None = Field(
        None, description="Year associated with the task"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class TaskUpdateDto(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=60, description="Title or name of the task"
    )
    type: str | None = Field(
        default=None, max_length=10, description="Type of the entry (e.g., 'Exam', 'Assignment', 'Task')"
    )
    url: str | None = Field(
        default=None, max_length=100, description="URL where the task should be submitted"
    )
    urls: list[str] | None = Field(
        default=None, description="List of Google Drive file URLs"
    )
    links: list[TaskLinkDto] | None = Field(
        default=None, description="List of external links objects"
    )
    details: dict | None = Field(
        default=None, description="Additional details about the task"
    )
    deadline: datetime | None = Field(
        default=None, description="Datetime for the task deadline"
    )
    due_date: datetime | None = Field(
        default=None, description="Datetime for the task due date"
    )
    author_id: int | None = Field(
        default=None, gt=0, description="ID of the author"
    )
    subject_id: int | None = Field(
        default=None, gt=0, description="ID of the subject this task belongs to"
    )
    department_id: int | None = Field(
        default=None, gt=0, description="ID of the department this task belongs to"
    )
    faculty_id: int | None = Field(
        default=None, description="ID of the faculty this task belongs to"
    )
    year_id: int | None = Field(
        default=None, description="ID of the year this task belongs to"
    )


class TaskSearchDto(BaseSearchDto, BaseModel):
    name: str | None = Field(
        default=None, description="Name/Title to search by"
    )
    type: str | None = Field(
        default=None, description="Type to filter by (e.g., 'Task', 'Exam')"
    )
    faculty_id: int | None = Field(
        default=None, description="ID of Faculty to filter by"
    )
    department_id: int | None = Field(
        default=None, description="ID of Department to filter by"
    )
    year_id: int | None = Field(
        default=None, description="ID of Year to filter by"
    )
    subject_id: int | None = Field(
        default=None, description="ID of Subject to filter by"
    )
    author_id: int | None = Field(
        default=None, description="ID of Author to filter by"
    )
    start_date: str | None = Field(
        default=None, description="Start date to filter by (>=)"
    )
    end_date: str | None = Field(
        default=None, description="End date to filter by (<=)"
    )