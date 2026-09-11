from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.dtos.releaseDtos import ReleaseResponseDto

from core.dtos.baseDtos import BaseSearchDto

class VersionResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the version")
    version_number: int | None = Field(None, description="Major version number")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last updated timestamp")

    # Relationships
    releases: list[ReleaseResponseDto] | None = Field(
        None, description="List of releases associated with this version"
    )

    model_config = {
        "from_attributes": True,
    }


class VersionSearchDto(BaseSearchDto):
    id: int | None = Field(None, description="Filter by version ID")
    version_number: int | None = Field(
        None, description="Filter by major version number"
    )
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
