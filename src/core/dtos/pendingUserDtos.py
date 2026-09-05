from __future__ import annotations
from datetime import datetime
from typing import TypedDict, TYPE_CHECKING
from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto
    from core.dtos.attachmentDtos import AttachmentResponseDto


class PendingUserResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the user")
    url: str | None = Field(default=None, description="URL of the user approval image")
    created_at: datetime | None = Field(
        default=None, description="Timestamp when the pending user was created"
    )
    updated_at: datetime | None = Field(
        default=None, description="Timestamp when the pending user was last updated"
    )

    # Relationships
    user: UserResponseDto | None = Field(
        default=None, description="The user associated with this pending user"
    )
    attachment: AttachmentResponseDto | None = Field(
        default=None, description="The attachment associated with this pending user"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }
