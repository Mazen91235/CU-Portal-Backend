from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .subjectDtos import SubjectResponseDto
    from .userDtos import UserResponseDto
    from .weekDtos import WeekResponseDto
    from .attachmentDtos import AttachmentResponseDto

from core.dtos.baseDtos import BaseSearchDto


class MaterialCreateDto(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=200, description="Name of the material"
    )
    material_type: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Type of the material (file, folder, youtube, drive, external.)",
    )
    subject_id: int = Field(..., description="ID of the associated subject")
    parent_id: int | None = Field(
        default=None, description="ID of the parent material (for hierarchy)"
    )
    week_id: int | None = Field(default=None, description="ID of the associated week")
    details: dict | None = Field(
        default=None, description="Additional metadata about the material (like url)"
    )


class MaterialResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the material")
    name: str | None = Field(
        default=None, max_length=200, description="Name of the material"
    )
    material_type: str | None = Field(
        default=None,
        max_length=30,
        description="Type of the material (file, folder, youtube, drive, external.)",
    )
    details: dict | None = Field(
        default=None, description="Additional metadata about the material"
    )

    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last modification timestamp"
    )

    # Relationships
    author: UserResponseDto | None = Field(
        default=None, description="Author of the material"
    )

    subject: SubjectResponseDto | None = Field(
        default=None, description="Subject associated with the material"
    )

    parent_id: int | None = Field(
        default=None, description="Parent material ID (for hierarchy)"
    )

    children: list[MaterialResponseDto] | None = Field(
        default=None, description="List of child materials (for hierarchy)"
    )
    attachment: AttachmentResponseDto | None = Field(
        default=None, description="Attachment associated with the material"
    )
    week: WeekResponseDto | None = Field(
        default=None, description="Week associated with the material"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class MaterialUpdateDto(BaseModel):
    name: str = Field(..., max_length=200, description="Updated name of the material")
    material_type: str = Field(
        ..., max_length=30, description="Updated type of the material"
    )
    week_id: int | None = Field(default=None, description="ID of the associated week")
    details: dict | None = Field(
        default=None,
        description="Updated additional metadata about the material (like url)",
    )


class MaterialsDeleteDto(BaseModel):
    material_ids: list[int] = Field(
        ..., min_length=1, description="List of material IDs to delete"
    )


class MaterialSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the material to filter by")
    material_type: str | None = Field(
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
    week_id: int | None = Field(
        default=None, description="ID of the associated week to filter by"
    )
    author_id: int | None = Field(
        default=None, description="ID of the author to filter by"
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
    subject_id: int = Field(..., description="ID of the subject for the operation")
    destination_id: int | None = Field(None, description="Destination parent ID")


class MaterialsFetchFromDriveDto(BaseModel):
    url: str = Field(..., description="Drive URL to fetch materials from")
    subject_id: int | None = Field(
        None, description="ID of the associated subject for the fetched materials"
    )
    parent_id: int | None = Field(
        None, description="ID of the parent material for the fetched materials"
    )


class MaterialDownloadManyDto(BaseModel):
    material_ids: list[int] = Field(
        ..., min_length=1, description="List of material IDs to download"
    )
