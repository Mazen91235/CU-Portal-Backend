from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto
    from .baseDtos import BaseSearchDto


class YearCreateDto(BaseModel):
    year: int = Field(..., ge=1900, le=3000, description="Academic year (positive 4-digit number)")


class YearUpdateDto(BaseModel):
    year: int = Field(..., ge=1900, le=3000, description="Academic year (positive 4-digit number)")


class YearSearchDto(BaseSearchDto):
    year: int | None = Field(default=None, description="Academic year to filter by")


class YearResponseDto(BaseModel):
    id: int = Field(..., description="ID of the year")
    year: int = Field(..., description="Academic year value")
    details: dict | None = Field(default=None, description="Additional details")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    # Relationships
    users: list[UserResponseDto] | None = Field(None, description="Users in this year")

    model_config = {
        "from_attributes": True,
    }
