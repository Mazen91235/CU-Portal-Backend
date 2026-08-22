from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Any
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .userDtos import UserResponseDto
    from .subjectDtos import SubjectResponseDto
    from .departmentDtos import DepartmentResponseDto
    from .yearDtos import YearResponseDto
    from .facultyDtos import FacultyResponseDto
    from .attachmentDtos import AttachmentResponseDto

from core.dtos.baseDtos import BaseSearchDto


class AnnouncementCreateDto(BaseModel):
    title: str = Field(
        ..., min_length=1, max_length=255, description="Title of the announcement"
    )
    content: str = Field(
        ..., min_length=1, max_length=1000, description="Content of the announcement"
    )
    date: str | None = Field(
        default=None, description="Date string for the announcement"
    )
    subject_id: int = Field(
        ..., gt=0, description="ID of the subject this announcement belongs to"
    )
    faculty_id: int | None = Field(default=None, gt=0, description="ID of the faculty")
    department_id: int | None = Field(
        default=None, gt=0, description="ID of the department"
    )
    year_id: int | None = Field(
        default=None, gt=0, description="ID of the academic year"
    )
    urls: list[str] = Field(
        default_factory=list,
        description="List of Google Drive file URLs attached to the announcement",
    )
    links: list[dict[str, str]] = Field(
        default_factory=list, description="List of external links"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional details dictionary"
    )


class AnnouncementResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the announcement")
    title: str | None = Field(default=None, description="Title of the announcement")
    content: str | None = Field(default=None, description="Content of the announcement")
    date: datetime | None = Field(
        default=None, description="Scheduled date of the announcement"
    )
    urls: list[str] | None = Field(
        default_factory=list, description="List of attached file URLs"
    )
    links: list[dict[str, str]] | None = Field(
        default_factory=list, description="List of attached links"
    )
    details: dict | None = Field(
        default_factory=dict, description="Additional details (e.g., files_data)"
    )
    created_at: datetime | None = Field(
        default=None, description="Creation date of the announcement"
    )
    modified_at: datetime | None = Field(
        default=None, description="Last update date of the announcement"
    )

    # Relationships
    author: UserResponseDto | None = Field(
        default=None, description="Author who created the announcement"
    )
    subject: SubjectResponseDto | None = Field(
        default=None, description="Subject associated with the announcement"
    )
    faculty: FacultyResponseDto | None = Field(
        default=None, description="Faculty associated with the announcement"
    )
    department: DepartmentResponseDto | None = Field(
        default=None, description="Department associated with the announcement"
    )
    year: YearResponseDto | None = Field(
        default=None, description="Academic year associated with the announcement"
    )
    attachments: list[AttachmentResponseDto] = Field(
        default_factory=list,
        description="Attachments (files or links) associated with the announcement",
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class AnnouncementUpdateDto(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Title of the announcement",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Content of the announcement",
    )
    date: str | None = Field(
        default=None, description="ISO formatted date string for the announcement"
    )
    subject_id: int = Field(
        ..., gt=0, description="ID of the subject this announcement belongs to"
    )
    faculty_id: int | None = Field(default=None, gt=0, description="ID of the faculty")
    department_id: int | None = Field(
        default=None, gt=0, description="ID of the department"
    )
    year_id: int | None = Field(
        default=None, gt=0, description="ID of the academic year"
    )
    urls: list[str] = Field(
        default_factory=list,
        description="List of Google Drive file URLs attached to the announcement",
    )
    links: list[dict[str, str]] = Field(
        default_factory=list, description="List of external links"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional details dictionary"
    )


class AnnouncementDeleteDto(BaseModel):
    id: int = Field(..., description="ID of the announcement to delete")


class AnnouncementSearchDto(BaseSearchDto):
    id: int | None = Field(
        default=None, description="ID of the announcement to filter by"
    )
    subject_id: int | None = Field(
        default=None, description="ID of Subject to filter by"
    )
    faculty_id: int | None = Field(
        default=None, description="ID of Faculty to filter by"
    )
    department_id: int | None = Field(
        default=None, description="ID of Department to filter by"
    )
    year_id: int | None = Field(default=None, description="ID of Year to filter by")
    author_id: int | None = Field(default=None, description="ID of Author to filter by")
    date_from: str | None = Field(
        default=None, description="Start date to filter announcements"
    )
    date_to: str | None = Field(
        default=None, description="End date to filter announcements"
    )
