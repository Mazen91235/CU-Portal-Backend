from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.facultyDtos import FacultyResponseDto
    from core.dtos.departmentDtos import DepartmentResponseDto
    from core.dtos.yearDtos import YearResponseDto
    from core.dtos.materialDtos import MaterialResponseDto
    from core.dtos.weekItemDtos import WeekItemResponseDto

from core.dtos.baseDtos import BaseSearchDto


class WeekCreateDto(BaseModel):
    week_number: int = Field(..., ge=1, description="Week number")
    start_date: datetime = Field(..., description="Start date of the week")
    faculty_id: int = Field(..., description="Faculty ID associated with the week")
    department_id: int = Field(
        ..., description="Department ID associated with the week"
    )
    year_id: int = Field(..., description="Year ID associated with the week")


class WeekResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the week")
    week_number: int | None = Field(default=None, description="Week number")
    start_date: datetime | None = Field(
        default=None, description="Start date of the week"
    )
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    # Relationships
    faculty: FacultyResponseDto | None = Field(
        default=None, description="Faculty details"
    )
    department: DepartmentResponseDto | None = Field(
        default=None, description="Department details"
    )
    year: YearResponseDto | None = Field(default=None, description="Year details")
    materials: list[MaterialResponseDto] | None = Field(
        default=None, description="Materials associated with this week"
    )
    week_items: list[WeekItemResponseDto] | None = Field(
        default=None, description="Week items associated with this week"
    )

    model_config = {
        "from_attributes": True,
    }


class WeekUpdateDto(BaseModel):
    week_number: int = Field(..., ge=1, description="Week number")
    start_date: datetime = Field(..., description="Start date of the week")
    faculty_id: int = Field(..., description="Faculty ID")
    department_id: int = Field(..., description="Department ID")
    year_id: int = Field(..., description="Year ID")


class WeekSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the week to filter by")
    week_number: int | None = Field(
        default=None, description="Week number to filter by"
    )
    faculty_id: int | None = Field(default=None, description="Faculty ID to filter by")
    department_id: int | None = Field(
        default=None, description="Department ID to filter by"
    )
    year_id: int | None = Field(default=None, description="Year ID to filter by")
    start_date_from: datetime | None = Field(
        default=None, description="Filter weeks starting after this date"
    )
    start_date_to: datetime | None = Field(
        default=None, description="Filter weeks starting before this date"
    )
    start_date_includes: datetime | None = Field(
        default=None, description="Filter weeks that include this date"
    )
    created_at_from: datetime | None = Field(
        default=None, description="Filter weeks created after this date"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Filter weeks created before this date"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Filter weeks updated after this date"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Filter weeks updated before this date"
    )
