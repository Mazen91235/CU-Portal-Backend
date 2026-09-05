from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto
    from core.dtos.subjectDtos import SubjectResponseDto
    from core.dtos.taskDtos import TaskResponseDto
    from core.dtos.announcementDtos import AnnouncementResponseDto
    from core.dtos.weekDtos import WeekResponseDto

from core.dtos.baseDtos import BaseSearchDto


class YearCreateDto(BaseModel):
    year: int = Field(
        ..., ge=1900, le=3000, description="Academic year (positive 4-digit number)"
    )


class YearResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the year")
    year: int | None = Field(default=None, description="Academic year value")
    details: dict | None = Field(default=None, description="Additional details")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    # Relationships
    users: list[UserResponseDto] | None = Field(
        default=None, description="Users in this year"
    )
    subjects: list[SubjectResponseDto] | None = Field(
        default=None, description="Subjects in this year"
    )
    tasks: list[TaskResponseDto] | None = Field(
        default=None, description="Tasks in this year"
    )
    announcements: list[AnnouncementResponseDto] | None = Field(
        default=None, description="Announcements in this year"
    )
    weeks: list[WeekResponseDto] | None = Field(
        default=None, description="Weeks in this year"
    )

    model_config = {
        "from_attributes": True,
    }


class YearUpdateDto(BaseModel):
    year: int = Field(
        ..., ge=1900, le=3000, description="Academic year (positive 4-digit number)"
    )


class YearSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the year to filter by")
    created_at_from: datetime | None = Field(
        default=None, description="Filter years created after this date"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Filter years created before this date"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Filter years updated after this date"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Filter years updated before this date"
    )
