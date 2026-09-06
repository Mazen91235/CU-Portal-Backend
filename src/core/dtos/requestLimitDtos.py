from __future__ import annotations
from datetime import datetime
from typing import TypedDict, TYPE_CHECKING
from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto

from .baseDtos import BaseSearchDto


class RequestLimitSearchDto(BaseSearchDto):
    id: int | None = Field(
        default=None, description="ID of the request limit to filter by"
    )
    ip: str | None = Field(default=None, description="IP address to filter by")
    route: str | None = Field(default=None, description="Route to filter by")
    status: bool | None = Field(default=None, description="Status to filter by")
    user_id: int | None = Field(default=None, description="User ID to filter by")
    created_at_from: datetime | None = Field(
        default=None, description="Creation Date from to filter by"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Creation Date to to filter by"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Last Update Date from to filter by"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Last Update Date to to filter by"
    )
