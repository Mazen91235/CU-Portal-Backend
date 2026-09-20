from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.dtos.releaseDtos import ReleaseResponseDto
    from core.entities.releaseItem import ReleaseItem


class ReleaseItemMutationDto(BaseModel):
    item_type: ReleaseItem.ItemType = Field(
        ...,
        description="Type of the item (Feature, Improvement, Refactoring, Security Fix, Bug Fix)",
    )
    content: str = Field(
        ..., min_length=1, max_length=600, description="Content/description of the item"
    )


class ReleaseItemResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the release item")
    item_type: ReleaseItem.ItemType | None = Field(None, description="Type of the item")
    content: str | None = Field(None, description="Content/description of the item")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last updated timestamp")

    # Relationships
    release: ReleaseResponseDto | None = Field(
        None, description="Release details associated with this item"
    )

    model_config = {
        "from_attributes": True,
    }
