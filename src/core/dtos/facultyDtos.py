from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field
from .baseDtos import BaseSearchDto


class FacultyCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=40, description="Name of Faculty")


class FacultyResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the faculty")
    name: str = Field(..., description="Name of Faculty")
    details: dict | None = Field(
        None, description="Additional details about the faculty"
    )
    created_at: datetime | None = Field(
        None, description="Creation Date of the faculty"
    )
    updated_at: datetime | None = Field(
        None, description="Last Update Date of the faculty"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class FacultyUpdateDto(BaseModel):
    id: int = Field(..., description="ID of the faculty to update")
    name: str = Field(..., min_length=1, max_length=40, description="Name of Faculty")


class FacultyDeleteDto(BaseModel):
    id: int = Field(..., description="ID of Faculty to delete")


class FacultySearchDto(BaseSearchDto, BaseModel):
    id: int | None = Field(default=None, description="ID of Faculty to filter by")
