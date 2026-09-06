from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.entities.department import Department
    from core.dtos.userDtos import UserResponseDto
    from core.dtos.facultyDtos import FacultyResponseDto
    from core.dtos.subjectDtos import SubjectResponseDto
    from core.dtos.taskDtos import TaskResponseDto
    from core.dtos.announcementDtos import AnnouncementResponseDto
    from core.dtos.weekDtos import WeekResponseDto

from core.dtos.baseDtos import BaseSearchDto


class DepartmentCreateDto(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=40, description="Name of the department"
    )
    code: str = Field(
        ..., min_length=1, max_length=10, description="Code of the department"
    )
    faculty_id: int = Field(
        ..., description="Faculty ID associated with the department"
    )
    study_type: Department.StudyType = Field(
        ..., description="Study type (Mainstream, Credit, or Both)"
    )


class DepartmentResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the department")
    name: str | None = Field(default=None, description="Name of the department")
    code: str | None = Field(default=None, description="Code of the department")
    details: dict | None = Field(default=None, description="Additional details")
    study_type: Department.StudyType | None = Field(
        default=None, description="Study type of the department"
    )
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    # Relationships
    faculty: FacultyResponseDto | None = Field(
        default=None, description="Faculty associated with the department"
    )
    users: list[UserResponseDto] | None = Field(
        default=None, description="Users in this department"
    )
    subjects: list[SubjectResponseDto] | None = Field(
        default=None, description="Subjects in this department"
    )
    announcements: list[AnnouncementResponseDto] | None = Field(
        default=None, description="Announcements in this department"
    )
    weeks: list[WeekResponseDto] | None = Field(
        default=None, description="Weeks in this department"
    )

    model_config = {
        "from_attributes": True,
    }


class DepartmentUpdateDto(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=40, description="Name of the department"
    )
    code: str = Field(
        ..., min_length=1, max_length=10, description="Code of the department"
    )
    faculty_id: int = Field(
        ..., description="Faculty ID associated with the department"
    )
    study_type: Department.StudyType = Field(
        ..., description="Study type (Mainstream or Credit)"
    )


class DepartmentSearchDto(BaseSearchDto):
    id: int | None = Field(
        default=None, description="ID of the department to filter by"
    )
    faculty_id: int | None = Field(default=None, description="Faculty ID to filter by")
    study_type: Department.StudyType | None = Field(
        default=None, description="Study type to filter by"
    )
    created_at_from: datetime | None = Field(
        default=None, description="Filter departments created after this date"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Filter departments created before this date"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Filter departments updated after this date"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Filter departments updated before this date"
    )
