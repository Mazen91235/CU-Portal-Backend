from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from core.dtos.baseDtos import BaseSearchDto
from core.dtos.versionDtos import VersionResponseDto
from core.dtos.releaseItemDtos import ReleaseItemCreateDto, ReleaseItemResponseDto


class ReleaseCreateDto(BaseModel):
    release_number: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="Release version in format Major.Minor.BugFix (e.g., 2.1.3)")
    title: str = Field(..., min_length=1, max_length=100, description="Title of the release")
    date: str = Field(..., description="Date of the release in ISO format")
    release_items: list[ReleaseItemCreateDto] = Field(default_factory=list, description="Items included in this release")


class ReleaseUpdateDto(BaseModel):
    release_number: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="Release version in format Major.Minor.BugFix")
    title: str = Field(..., min_length=1, max_length=100, description="Title of the release")
    date: str = Field(..., description="Date of the release in ISO format")
    release_items: list[ReleaseItemCreateDto] = Field(default_factory=list, description="Updated list of items (replaces old items)")


class ReleaseSearchDto(BaseSearchDto):
    release_number: str | None = Field(None, description="Filter by exact release number")
    title: str | None = Field(None, description="Search by title")
    version_id: int | None = Field(None, description="Filter by parent Version ID")


class ReleaseResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the release")
    release_number: str | None = Field(None, description="Release version number")
    title: str | None = Field(None, description="Title of the release")
    date: datetime | None = Field(None, description="Date of the release")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last updated timestamp")

    # Relationships
    version: VersionResponseDto | None = Field(None, description="Parent major version")
    release_items: list[ReleaseItemResponseDto] | None = Field(None, description="Items associated with this release")

    model_config = {
        "from_attributes": True,
    }