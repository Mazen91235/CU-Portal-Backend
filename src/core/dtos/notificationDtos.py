from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.entities.notification import Notification


class NotificationResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the notification")
    content: str | None = Field(None, description="Content of the notification")
    type: Notification.Type | None = Field(
        None, description="Type of the notification (e.g., task, announcement)"
    )
    parent_id: int | None = Field(None, description="ID of the related parent entity")
    url: str | None = Field(None, description="URL to redirect to")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    model_config = {
        "from_attributes": True,
    }
