from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .subjectDtos import SubjectResponseDto
    from .userDtos import UserResponseDto

from core.dtos.baseDtos import BaseSearchDto


class MaterialCreateDto(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=200, description="Name of the material"
    )
    type: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Type of the material (file, folder, youtube, drive, external.)",
    )
    url: str | None = Field(
        None, max_length=255, description="Drive URL of the material"
    )
    subject_id: int | None = Field(
        default=None, description="ID of the associated subject"
    )
    parent_id: int | None = Field(
        default=None, description="ID of the parent material (for hierarchy)"
    )


class MaterialResponseDto(BaseModel):
    id: int = Field(..., description="ID of the material")
    name: str | None = Field(None, max_length=200, description="Name of the material")
    type: str = Field(
        ...,
        max_length=30,
        description="Type of the material (file, folder, youtube, drive, external.)",
    )
    url: str | None = Field(
        None, max_length=255, description="Drive URL of the material"
    )
    details: dict | None = Field(
        default=None, description="Additional metadata about the material"
    )

    created_at: datetime | None = Field(None, description="Creation timestamp")
    modified_at: datetime | None = Field(
        None, description="Last modification timestamp"
    )

    # Relationships
    author: UserResponseDto | None = Field(None, description="Author of the material")

    subject: SubjectResponseDto | None = Field(
        None, description="Subject associated with the material"
    )

    parent_id: int | None = Field(
        None, description="Parent material ID (for hierarchy)"
    )

    children: list[MaterialResponseDto] | None = Field(
        None, description="List of child materials (for hierarchy)"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class MaterialUpdateDto(BaseModel):
    name: str | None = Field(
        None, max_length=200, description="Updated name of the material"
    )
    description: str | None = Field(
        None, max_length=500, description="Updated description"
    )
    url: str | None = Field(None, max_length=255, description="Updated URL")


class MaterialsDeleteDto(BaseModel):
    material_ids: list[int] = Field(
        ..., min_length=1, description="List of material IDs to delete"
    )


class MaterialSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the material to filter by")
    type: str | None = Field(
        default=None,
        max_length=30,
        description="Type of the material to filter by (file, folder, youtube, drive, external.)",
    )
    subject_id: int | None = Field(
        default=None, description="ID of the associated subject to filter by"
    )
    parent_id: int | None = Field(
        default=None, description="ID of the parent material to filter by"
    )
    created_at_from: datetime | None = Field(
        default=None, description="Filter materials created after this date"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Filter materials created before this date"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Filter materials updated after this date"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Filter materials updated before this date"
    )


class MaterialsCopyOrMoveDto(BaseModel):
    material_ids: list[int] = Field(
        ..., min_length=1, description="List of material IDs"
    )
    destination_id: int | None = Field(None, description="Destination parent ID")


class MaterialsFetchFromDriveDto(BaseModel):
    url: str = Field(..., description="Drive URL to fetch materials from")
    subject_id: int | None = Field(
        None, description="ID of the associated subject for the fetched materials"
    )
    parent_id: int | None = Field(
        None, description="ID of the parent material for the fetched materials"
    )
