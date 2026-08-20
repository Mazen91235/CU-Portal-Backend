from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field
from .userDtos import UserResponseDto

if TYPE_CHECKING:
    from .facultyDtos import FacultyResponseDto
    from .departmentDtos import DepartmentResponseDto
    from .yearDtos import YearResponseDto
    from .taskDtos import TaskResponseDto
    from .announcementDtos import AnnouncementResponseDto
    from .materialDtos import MaterialResponseDto

from core.dtos.baseDtos import BaseSearchDto


class SubjectCreateDto(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=50, description="Name of the subject"
    )
    code: str = Field(
        ..., min_length=1, max_length=15, description="Unique code of the subject"
    )
    faculty_id: int = Field(
        ..., gt=0, description="ID of the faculty this subject belongs to"
    )
    department_id: int = Field(
        ..., gt=0, description="ID of the department this subject belongs to"
    )
    year_id: int = Field(
        ..., gt=0, description="ID of the year this subject belongs to"
    )
    credits: int | None = Field(
        None, gt=0, description="Number of credits for the subject"
    )
    details: dict | None = Field(
        None,
        description="Additional details about the subject like description, max_students, etc.",
    )


class SubjectResponseDto(BaseModel):
    id: int = Field(..., description="ID of the subject")
    name: str = Field(..., description="Name of the subject")
    code: str | None = Field(None, description="Code of the subject")
    details: dict | None = Field(
        None, description="Additional details about the subject"
    )
    is_old: bool = Field(
        ..., description="Whether this subject is deprecated/no longer offered"
    )
    year_rank: int | None = Field(
        None, description="Rank/order of the subject within its year"
    )
    term: int | None = Field(
        None, description="Term/semester the subject is offered in"
    )
    credits: int | None = Field(None, description="Number of credits for the subject")
    created_at: datetime | None = Field(
        None, description="Timestamp when the subject was created"
    )
    updated_at: datetime | None = Field(
        None, description="Timestamp when the subject was last updated"
    )
    # Relationships
    faculty: FacultyResponseDto | None = Field(
        None, description="Faculty associated with the subject"
    )
    department: DepartmentResponseDto | None = Field(
        None, description="Department associated with the subject"
    )
    year: YearResponseDto | None = Field(
        None, description="Year associated with the subject"
    )
    users: list[UserResponseDto] | None = Field(
        None, description="Enrolled users associated with the subject"
    )
    tasks: list[TaskResponseDto] | None = Field(
        None, description="Tasks associated with the subject"
    )
    announcements: list[AnnouncementResponseDto] | None = Field(
        None, description="Announcements associated with the subject"
    )
    materials: list[MaterialResponseDto] | None = Field(
        None, description="Materials associated with the subject"
    )

    model_config = {"from_attributes": True}


class SubjectUpdateDto(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=50, description="Name of the subject"
    )
    code: str = Field(
        ..., min_length=1, max_length=15, description="Unique code of the subject"
    )
    faculty_id: int = Field(
        ..., gt=0, description="ID of the faculty this subject belongs to"
    )
    department_id: int = Field(
        ..., gt=0, description="ID of the department this subject belongs to"
    )
    year_id: int = Field(
        ..., gt=0, description="ID of the year this subject belongs to"
    )
    credits: int | None = Field(
        None, gt=0, description="Number of credits for the subject"
    )
    details: dict | None = Field(
        None,
        description="Additional details about the subject like description, max_students, etc.",
    )
    is_old: bool | None = Field(
        default=None, description="Whether the subject is deprecated"
    )


class SubjectSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of Subject to filter by")
    faculty_id: int | None = Field(
        default=None, description="ID of Faculty to filter by"
    )
    department_id: int | None = Field(
        default=None, description="ID of Department to filter by"
    )
    year_id: int | None = Field(default=None, description="ID of Year to filter by")
    is_old: bool | None = Field(
        default=None, description="Whether the subject is deprecated"
    )
