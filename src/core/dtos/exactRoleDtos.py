from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.roleDtos import RoleResponseDto


class ExactRoleResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the role")
    name: str = Field(..., description="Name of Role")
    created_at: datetime | None = Field(
        None, description="Timestamp when the role was created"
    )
    updated_at: datetime | None = Field(
        None, description="Timestamp when the role was last updated"
    )
    # Relationships
    roles: list[RoleResponseDto] | None = Field(
        None, description="List of roles associated with the exact role"
    )
