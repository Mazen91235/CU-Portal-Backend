from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .userDtos import UserResponseDto
    from .pendingUserDtos import PendingUserResponseDto
    from .materialDtos import MaterialResponseDto
    from .taskDtos import TaskResponseDto
    from .announcementDtos import AnnouncementResponseDto


class AttachmentResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the attachment")
    is_file: bool | None = Field(
        default=None, description="Indicates if the attachment is a file"
    )
    url: str | None = Field(default=None, description="URL of the attachment")
    details: dict | None = Field(
        default_factory=dict,
        description="Additional details (e.g., files_data, fetched, link_title)",
    )
    created_at: datetime | None = Field(
        default=None, description="Creation date of the attachment"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last update date of the attachment"
    )

    # Relationships
    author: UserResponseDto | None = Field(
        default=None, description="Author who created the attachment"
    )
    user: UserResponseDto | None = Field(
        default=None, description="User associated with the attachment"
    )
    pending_user: PendingUserResponseDto | None = Field(
        default=None, description="Pending user associated with the attachment"
    )
    material: MaterialResponseDto | None = Field(
        default=None, description="Material associated with the attachment"
    )
    task: TaskResponseDto | None = Field(
        default=None, description="Task associated with the attachment"
    )
    announcement: AnnouncementResponseDto | None = Field(
        default=None, description="Announcement associated with the attachment"
    )
    # event_logo: EventResponseDto | None = Field(
    #     default=None, description="Event associated with the attachment as a logo"
    # )
    # event: EventResponseDto | None = Field(
    #     default=None, description="Event associated with the attachment"
    # )
    # event_organizer_logo: EventOrganizerResponseDto | None = Field(
    #     default=None, description="Event organizer associated with the attachment as a logo"
    # )
    # event_organizer: EventOrganizerResponseDto | None = Field(
    #     default=None, description="Event organizer associated with the attachment"
    # )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }
