from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.entities.notification import Notification


class NotificationCreateDto(BaseModel):
    notification_type: Notification.NotificationType = Field(
        ..., description="Type of the notification (e.g., task, announcement)"
    )
    parent_id: int = Field(..., description="ID of the related parent entity")
    content: str = Field(..., description="Content of the notification")
    url: str | None = Field(default=None, description="URL to redirect to")
    faculty_id: int | None = Field(
        default=None, description="ID of the related faculty (if applicable)"
    )
    department_id: int | None = Field(
        default=None, description="ID of the related department (if applicable)"
    )
    year_id: int | None = Field(
        default=None, description="ID of the related year (if applicable)"
    )
    subject_id: int | None = Field(
        default=None, description="ID of the related subject (if applicable)"
    )
    user_ids: set[int] | None = Field(
        default=None, description="Set of user IDs to send the notification to"
    )


class NotificationResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the notification")
    content: str | None = Field(default=None, description="Content of the notification")
    notification_type: Notification.NotificationType | None = Field(
        default=None, description="Type of the notification (e.g., task, announcement)"
    )
    seen: bool | None = Field(
        default=None, description="Whether the notification has been seen"
    )
    parent_id: int | None = Field(
        default=None, description="ID of the related parent entity"
    )
    url: str | None = Field(default=None, description="URL to redirect to")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")

    model_config = {
        "from_attributes": True,
    }

class NotificationMarkManyAsSeenDto(BaseModel):
    notification_ids: list[int] = Field(
        ..., min_length=1, description="List of notification IDs to mark as seen"
    )