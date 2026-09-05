from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto

from core.dtos.baseDtos import BaseSearchDto


class NoteResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the note")
    title: str | None = Field(default=None, description="Title of the note")
    content: str | None = Field(default=None, description="Content of the note")
    date: datetime | None = Field(default=None, description="Date of the note")
    created_at: datetime | None = Field(
        default=None, description="Creation Date of the message"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last Update Date of the message"
    )

    # Relationships
    author: UserResponseDto | None = Field(
        default=None, description="User who created the note"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }
