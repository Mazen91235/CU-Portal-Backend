from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING
from core.dtos.baseDtos import BaseSearchDto

if TYPE_CHECKING:
    from core.dtos.releaseDtos import ReleaseResponseDto


class VersionSearchDto(BaseSearchDto):
    version_number: int | None = Field(None, description="Filter by major version number")


class VersionResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the version")
    version_number: int | None = Field(None, description="Major version number")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last updated timestamp")
    
    # Exclude nested releases to avoid circular recursion loops in simple responses, 
    # but it can be included if mapped explicitly.
    
    model_config = {
        "from_attributes": True,
    }