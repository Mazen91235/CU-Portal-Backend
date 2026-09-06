from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto
    from core.dtos.subjectDtos import SubjectResponseDto
    from core.dtos.announcementDtos import AnnouncementResponseDto
    from core.dtos.departmentDtos import DepartmentResponseDto
    from core.dtos.taskDtos import TaskResponseDto
    from core.dtos.weekDtos import WeekResponseDto

from core.dtos.baseDtos import BaseSearchDto


class FacultyCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=40, description="Name of Faculty")


class FacultyResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the faculty")
    name: str | None = Field(default=None, description="Name of Faculty")
    details: dict | None = Field(
        default=None, description="Additional details about the faculty"
    )
    created_at: datetime | None = Field(
        default=None, description="Creation Date of the faculty"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last Update Date of the faculty"
    )
    # Relationships
    users: list[UserResponseDto] | None = Field(
        default=None, description="List of users associated with the faculty"
    )
    departments: list[DepartmentResponseDto] | None = Field(
        default=None, description="List of departments associated with the faculty"
    )
    announcements: list[AnnouncementResponseDto] | None = Field(
        default=None, description="List of announcements associated with the faculty"
    )
    tasks: list[TaskResponseDto] | None = Field(
        default=None, description="List of tasks associated with the faculty"
    )
    subjects: list[SubjectResponseDto] | None = Field(
        default=None, description="List of subjects associated with the faculty"
    )
    weeks: list[WeekResponseDto] | None = Field(
        default=None, description="List of weeks associated with the faculty"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class FacultyUpdateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=40, description="Name of Faculty")


class FacultyDeleteDto(BaseModel):
    id: int = Field(..., description="ID of Faculty to delete")


class FacultySearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of Faculty to filter by")
