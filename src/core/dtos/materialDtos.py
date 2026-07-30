from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .subjectDtos import SubjectResponseDto
    from .userDtos import UserResponseDto


class MaterialResponseDto(BaseModel):
    id: int = Field(..., description="ID of the material")

    name: str | None = Field(None, max_length=200, description="Name of the material")
    type: str = Field(
        ..., max_length=30, description="Type of the material (file, link, video, etc.)"
    )
    url: str | None = Field(
        None, max_length=255, description="Primary URL of the material"
    )

    details: dict | None = Field(
        default=None, description="Additional metadata about the material"
    )

    created_at: datetime | None = Field(None, description="Creation timestamp")
    modified_at: datetime | None = Field(
        None, description="Last modification timestamp"
    )

    # Relationships
    subject: SubjectResponseDto | None = Field(
        None, description="Subject associated with the material"
    )

    parent_id: int | None = Field(
        None, description="Parent material ID (for hierarchy)"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class MaterialUpdateDto(BaseModel):
    id: int
    name: str | None = Field(
        None, max_length=200, description="Updated name of the material"
    )
    description: str | None = Field(
        None, max_length=500, description="Updated description"
    )
    url: str | None = Field(None, max_length=255, description="Updated URL")


class MaterialMinimalResponseDto(BaseModel):
    id: int = Field(..., description="ID of the material")

    name: str | None = Field(None, description="Name of the material")
    type: str = Field(..., description="Type of the material")
    url: str | None = Field(None, max_length=255, description="Material URL")

    created_at: datetime | None = Field(None, description="Creation timestamp")
    modified_at: datetime | None = Field(
        None, description="Last modification timestamp"
    )

    details: dict | None = Field(
        default=None, description="Additional metadata about the material"
    )

    parent_id: int | None = Field(None, description="Parent material ID")

    model_config = {
        "from_attributes": True,
    }


class MaterialExtendedResponseDto(BaseModel):
    id: int = Field(..., description="ID of the material")

    name: str | None = Field(None, max_length=200, description="Name of the material")
    type: str = Field(
        ..., max_length=30, description="Type of the material (file, link, video, etc.)"
    )
    url: str | None = Field(
        None, max_length=255, description="Primary URL of the material"
    )

    details: dict | None = Field(
        default=None, description="Additional metadata about the material"
    )

    created_at: datetime | None = Field(None, description="Creation timestamp")
    modified_at: datetime | None = Field(
        None, description="Last modification timestamp"
    )

    # Relationships
    subject: SubjectResponseDto | None = Field(
        None, description="Subject associated with the material"
    )

    parent: MaterialMinimalResponseDto | None = Field(
        None, description="Parent material (for hierarchy)"
    )

    author: UserResponseDto | None = Field(None, description="Author of the material")

    parent_id: int | None = Field(
        None, description="Parent material ID (for hierarchy)"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class MaterialsCopyAndMoveRequest(BaseModel):
    material_ids: list[int] = Field(
        ..., min_length=1, description="List of material IDs"
    )
    destination_id: int | None = Field(None, description="Destination parent ID")


class DriveMaterialPreviewDto(BaseModel):
    """Preview metadata returned when fetching a single file/folder from Drive
    before it's imported as a Material."""

    id: str = Field(..., description="Google Drive file ID")
    name: str = Field(..., description="File or folder name")
    mime_type: str = Field(..., description="MIME type as reported by Drive")
    file_type: str | None = Field(
        None, description="Normalized file type (image, pdf, doc, folder, etc.)"
    )
    size: str | None = Field(None, description="Human-readable file size")
    web_content_link: str | None = Field(
        None, description="Direct download link, if any"
    )
    web_view_link: str | None = Field(None, description="Drive view link")

    model_config = {
        "from_attributes": True,
    }
