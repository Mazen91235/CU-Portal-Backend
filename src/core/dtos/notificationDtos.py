from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.entities.notification import Notification


class NotificationResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the notification")
    content: str | None = Field(default=None, description="Content of the notification")
    notification_type: Notification.NotificationType | None = Field(
        default=None, description="Type of the notification (e.g., task, announcement)"
    )
    parent_id: int | None = Field(default=None, description="ID of the related parent entity")
    url: str | None = Field(default=None, description="URL to redirect to")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")

    model_config = {
        "from_attributes": True,
    }
