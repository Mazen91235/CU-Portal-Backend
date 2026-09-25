from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.notificationDtos import NotificationResponseDto
    from core.dtos.userDtos import UserResponseDto

from core.dtos.baseDtos import BaseSearchDto


class UserNotificationResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the user notification link")
    seen: bool | None = Field(
        default=None, description="Whether the user has seen the notification"
    )
    created_at: datetime | None = Field(
        default=None, description="When the notification was sent to the user"
    )

    # Relationships
    user: UserResponseDto | None = Field(
        default=None, description="The user associated with this notification"
    )
    notification: NotificationResponseDto | None = Field(
        default=None, description="The notification associated with this user"
    )

    model_config = {
        "from_attributes": True,
    }


class UserNotificationSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="Filter by user notification ID")
    user_id: int | None = Field(default=None, description="Filter by user ID")
    seen: bool | None = Field(
        default=None, description="Filter notifications by seen status"
    )
    notification_id: int | None = Field(
        default=None, description="Filter by notification ID"
    )
    created_at_from: datetime | None = Field(
        default=None,
        description="Filter by the timestamp when the notification was sent",
    )
    created_at_to: datetime | None = Field(
        default=None,
        description="Filter by the timestamp when the notification was sent",
    )
