from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from core.dtos.baseDtos import BaseSearchDto
from core.dtos.notificationDtos import NotificationResponseDto


class UserNotificationSearchDto(BaseSearchDto):
    seen: bool | None = Field(None, description="Filter notifications by seen status")


class UserNotificationResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the user notification link")
    seen: bool | None = Field(None, description="Whether the user has seen the notification")
    created_at: datetime | None = Field(None, description="When the notification was sent to the user")
    
    # Nested Relationship
    notification: NotificationResponseDto | None = Field(None, description="The actual notification data")

    model_config = {
        "from_attributes": True,
    }