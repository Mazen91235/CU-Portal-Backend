from __future__ import annotations
from datetime import datetime
from typing import TypedDict, TYPE_CHECKING
from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto


class PendingUserResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the user")
    url: str = Field(..., description="URL of the user approval image")
    created_at: datetime | None = Field(
        None, description="Timestamp when the pending user was created"
    )
    updated_at: datetime | None = Field(
        None, description="Timestamp when the pending user was last updated"
    )

    # Relationships
    user: UserResponseDto | None = Field(
        None, description="The user associated with this pending user"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }
