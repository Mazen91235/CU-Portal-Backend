from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class ReleaseItemCreateDto(BaseModel):
    item_type: str = Field(..., description="Type of the item (Feature, Enhancement, Refactoring, Security Fix, Bug Fix)")
    content: str = Field(..., min_length=1, max_length=255, description="Content/description of the item")


class ReleaseItemResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the release item")
    item_type: str | None = Field(None, description="Type of the item")
    content: str | None = Field(None, description="Content/description of the item")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last updated timestamp")

    model_config = {
        "from_attributes": True,
    }