from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.dtos.materialDtos import MaterialResponseDto
    from core.dtos.weekDtos import WeekResponseDto


class WeekItemMutationDto(BaseModel):
    week_id: int = Field(..., description="ID of the associated week")
    note: str = Field(
        default="", max_length=500, description="Optional note for this week-material association"
    )


class WeekItemResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the week item")
    note: str | None = Field(None, max_length=500, description="Note for this week-material association")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last updated timestamp")

    # Relationships
    week: WeekResponseDto | None = Field(
        None, description="Week associated with this item"
    )
    material: MaterialResponseDto | None = Field(
        None, description="Material associated with this item"
    )

    model_config = {
        "from_attributes": True,
    }
