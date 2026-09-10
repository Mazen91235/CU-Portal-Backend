from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.dtos.versionDtos import VersionResponseDto
    from core.dtos.releaseItemDtos import ReleaseItemMutationDto, ReleaseItemResponseDto

from core.dtos.baseDtos import BaseSearchDto


class ReleaseCreateDto(BaseModel):
    release_number: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Release version in format Major.Minor.BugFix (e.g., 2.1.3)",
    )
    title: str = Field(
        ..., min_length=1, max_length=100, description="Title of the release"
    )
    date: datetime = Field(..., description="Date of the release")
    release_items: list[ReleaseItemMutationDto] = Field(
        default_factory=list, description="Items included in this release"
    )


class ReleaseResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the release")
    release_number: str | None = Field(None, description="Release version number")
    title: str | None = Field(None, description="Title of the release")
    date: datetime | None = Field(None, description="Date of the release")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last updated timestamp")

    # Relationships
    version: VersionResponseDto | None = Field(None, description="Parent major version")
    release_items: list[ReleaseItemResponseDto] | None = Field(
        None, description="Items associated with this release"
    )

    model_config = {
        "from_attributes": True,
    }


class ReleaseUpdateDto(BaseModel):
    id: int = Field(..., description="ID of the release to update")
    release_number: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Release version in format Major.Minor.BugFix",
    )
    title: str = Field(
        ..., min_length=1, max_length=100, description="Title of the release"
    )
    date: datetime = Field(..., description="Date of the release")
    release_items: list[ReleaseItemMutationDto] = Field(
        default_factory=list, description="Updated list of items (replaces old items)"
    )


class ReleaseDeleteDto(BaseModel):
    id: int = Field(..., description="ID of the release to delete")


class ReleaseSearchDto(BaseSearchDto):
    id: int | None = Field(None, description="Filter by release ID")
    version_id: int | None = Field(None, description="Filter by parent Version ID")
    date_from: datetime | None = Field(
        None, description="Filter by release date (from)"
    )
    date_to: datetime | None = Field(None, description="Filter by release date (to)")
    created_at_from: datetime | None = Field(
        None, description="Filter by creation timestamp (from)"
    )
    created_at_to: datetime | None = Field(
        None, description="Filter by creation timestamp (to)"
    )
    updated_at_from: datetime | None = Field(
        None, description="Filter by last updated timestamp (from)"
    )
    updated_at_to: datetime | None = Field(
        None, description="Filter by last updated timestamp (to)"
    )
