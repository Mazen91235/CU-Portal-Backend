from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.taskDtos import TaskResponseDto
    from core.dtos.weekItemDtos import WeekItemResponseDto

from core.dtos.baseDtos import BaseSearchDto


class UserCompletionCreateDto(BaseModel):
    week_item_id: int | None = Field(
        default=None, gt=0, description="ID of the completed week item"
    )
    task_id: int | None = Field(
        default=None, gt=0, description="ID of the completed task"
    )


class UserCompletionResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the user completion")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    # Relationships
    user_id: int | None = Field(default=None, description="ID of the user")
    week_item_id: int | None = Field(
        default=None, description="ID of the completed week item"
    )
    task_id: int | None = Field(default=None, description="ID of the completed task")
    week_item: WeekItemResponseDto | None = Field(
        default=None, description="Week item associated with this completion"
    )
    task: TaskResponseDto | None = Field(
        default=None, description="Task associated with this completion"
    )

    model_config = {
        "from_attributes": True,
    }


class UserCompletionSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the user completion")
    user_id: int | None = Field(default=None, description="ID of the user")
    week_item_id: int | None = Field(
        default=None, description="ID of the completed week item"
    )
    task_id: int | None = Field(default=None, description="ID of the completed task")
    created_at_from: datetime | None = Field(
        default=None, description="Filter completions created after this date"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Filter completions created before this date"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Filter completions updated after this date"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Filter completions updated before this date"
    )
