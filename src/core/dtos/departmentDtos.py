from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto
    from .baseDtos import BaseSearchDto
    from core.dtos.facultyDtos import FacultyResponseDto
    from core.dtos.subjectDtos import SubjectResponseDto
    from core.dtos.taskDtos import TaskResponseDto
    from core.dtos.announcementDtos import AnnouncementResponseDto


class DepartmentCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=40, description="Name of the department")
    code: str = Field(..., min_length=1, max_length=10, description="Code of the department")
    faculty_id: int = Field(..., description="Faculty ID associated with the department")
    study_type: str = Field(..., description="Study type (Mainstream, Credit, or Both)")


class DepartmentUpdateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=40, description="Name of the department")
    code: str = Field(..., min_length=1, max_length=10, description="Code of the department")
    faculty_id: int = Field(..., description="Faculty ID associated with the department")
    study_type: str = Field(..., description="Study type (Mainstream or Credit)")


class DepartmentSearchDto(BaseSearchDto):
    name: str | None = Field(default=None, description="Name of the department to filter by")
    code: str | None = Field(default=None, description="Code of the department to filter by")
    faculty_id: int | None = Field(default=None, description="Faculty ID to filter by")
    study_type: str | None = Field(default=None, description="Study type to filter by")


class DepartmentResponseDto(BaseModel):
    id: int = Field(..., description="ID of the department")
    name: str = Field(..., description="Name of the department")
    code: str | None = Field(None, description="Code of the department")
    details: dict | None = Field(default=None, description="Additional details")
    study_type: str | None = Field(None, description="Study type of the department")
    faculty_id: int = Field(..., description="Faculty ID of the department")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    # Relationships
    faculty: FacultyResponseDto | None = Field(None, description="Faculty associated with the department")
    users: list[UserResponseDto] | None = Field(None, description="Users in this department")
    subjects: list[SubjectResponseDto] | None = Field(None, description="Subjects in this department")
    tasks: list[TaskResponseDto] | None = Field(None, description="Tasks in this department")
    announcements: list[AnnouncementResponseDto] | None = Field(None, description="Announcements in this department")

    model_config = {
        "from_attributes": True,
    }
