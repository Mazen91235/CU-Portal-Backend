from __future__ import annotations
from datetime import datetime
from typing import TypedDict, TYPE_CHECKING
from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto

from core.dtos.baseDtos import BaseSearchDto


class LogResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the user")
    action: str | None = Field(default=None, description="Action performed by the user")
    entity: str | None = Field(
        default=None, description="Entity on which the action was performed"
    )
    level: str | None = Field(
        default=None, description="Level of the log (e.g, info, warning, error)"
    )
    response_code: int | None = Field(
        default=None, description="Response code associated with the log"
    )
    message: str | None = Field(
        default=None, description="Message associated with the log"
    )
    details: dict | None = Field(
        default=None, description="Additional details associated with the log"
    )
    source: str | None = Field(
        default=None, description="Source of the log (e.g, LogService)"
    )
    route: str | None = Field(default=None, description="Route associated with the log")
    ip: str | None = Field(
        default=None, description="IP address associated with the log"
    )
    created_at: datetime | None = Field(
        default=None, description="Timestamp when the log was created"
    )
    updated_at: datetime | None = Field(
        default=None, description="Timestamp when the log was last updated"
    )

    # Relationships
    user: UserResponseDto | None = Field(
        default=None, description="User associated with the log"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class LogSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the log")
    level: str | None = Field(default=None, description="Level of the log")
    response_code: int | None = Field(
        default=None, description="Response code associated with the log"
    )
    source: str | None = Field(default=None, description="Source of the log")
    route: str | None = Field(default=None, description="Route associated with the log")
    ip: str | None = Field(
        default=None, description="IP address associated with the log"
    )
    user_id: int | None = Field(
        default=None, description="ID of the user associated with the log"
    )
    created_at_from: datetime | None = Field(
        default=None, description="Start date for log creation timestamp"
    )
    created_at_to: datetime | None = Field(
        default=None, description="End date for log creation timestamp"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Start date for log update timestamp"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="End date for log update timestamp"
    )
