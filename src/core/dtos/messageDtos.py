from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr, Field

from core.dtos.baseDtos import BaseSearchDto


class MessageCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=60, description="Sender name")
    email: EmailStr = Field(
        ..., min_length=1, max_length=100, description="Sender email address"
    )
    phone: str = Field(
        ..., min_length=1, max_length=20, description="Sender phone number"
    )
    content: str = Field(
        ..., min_length=1, max_length=500, description="Message content"
    )


class MessageResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the message")
    name: str | None = Field(default=None, description="Sender name")
    email: EmailStr | None = Field(default=None, description="Sender email address")
    phone: str | None = Field(default=None, description="Sender phone number")
    content: str | None = Field(default=None, description="Message content")
    created_at: datetime | None = Field(
        default=None, description="Creation Date of the message"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last Update Date of the message"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class MessageSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the message to filter by")
    created_at_from: datetime | None = Field(
        default=None, description="Creation Date from sender to filter by"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Creation Date to user to filter by"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Last Update Date from sender to filter by"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Last Update Date to user to filter by"
    )
