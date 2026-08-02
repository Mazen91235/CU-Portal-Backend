from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from core.dtos.baseDtos import BaseSearchDto
from core.dtos.notificationDtos import NotificationResponseDto
from core.dtos.userDtos import UserResponseDto


class UserNotificationResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the user notification link")
    seen: bool | None = Field(
        None, description="Whether the user has seen the notification"
    )
    created_at: datetime | None = Field(
        None, description="When the notification was sent to the user"
    )

    # Relationships
    user: UserResponseDto | None = Field(
        None, description="The user associated with this notification"
    )
    notification: NotificationResponseDto | None = Field(
        None, description="The notification associated with this user"
    )

    model_config = {
        "from_attributes": True,
    }


class UserNotificationSearchDto(BaseSearchDto, BaseModel):
    id: int | None = Field(None, description="Filter by user notification ID")
    seen: bool | None = Field(None, description="Filter notifications by seen status")
    user_id: int | None = Field(None, description="Filter by user ID")
    notification_id: int | None = Field(None, description="Filter by notification ID")
    created_at_from: datetime | None = Field(
        None, description="Filter by the timestamp when the notification was sent"
    )
    created_at_to: datetime | None = Field(
        None, description="Filter by the timestamp when the notification was sent"
    )
