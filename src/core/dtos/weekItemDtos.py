from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from core.dtos.materialDtos import MaterialResponseDto
    from core.dtos.weekDtos import WeekResponseDto
    from core.dtos.userDtos import UserResponseDto
    from core.dtos.userCompletionDtos import UserCompletionResponseDto


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
    completed_by_users: list[UserResponseDto] | None = Field(
        None, description="Users who have completed this week item"
    )
    user_completions: list[UserCompletionResponseDto] | None = Field(
        None, description="User completions associated with this week item"
    )

    model_config = {
        "from_attributes": True,
    }
