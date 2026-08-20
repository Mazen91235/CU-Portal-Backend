from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto
    from core.dtos.exactRoleDtos import ExactRoleResponseDto

from core.dtos.baseDtos import BaseSearchDto


class RoleCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=60, description="Name of Role")
    permissions: list[str] | None = Field(
        None, description="List of permissions associated with the role"
    )


class RoleResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the role")
    name: str = Field(..., description="Name of Role")
    level: int | None = Field(None, description="Level of the role")
    created_at: datetime | None = Field(
        None, description="Timestamp when the role was created"
    )
    updated_at: datetime | None = Field(
        None, description="Timestamp when the role was last updated"
    )
    users: list[UserResponseDto] | None = Field(
        None, description="List of users associated with the role"
    )
    exact_roles: list[ExactRoleResponseDto] | None = Field(
        None, description="List of exact roles associated with the role"
    )


class RoleUpdateDto(BaseModel):
    name: str | None = Field(
        None, min_length=1, max_length=60, description="Name of Role"
    )
    permissions: list[str] | None = Field(
        None, description="List of permissions associated with the role"
    )


class RoleDeleteDto(BaseModel):
    id: int = Field(..., gt=0, description="ID of the role to delete")


class RoleSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the role")
    name: str | None = Field(default=None, description="Name of the role")
    level: int | None = Field(default=None, description="Level of the role")
    created_at_from: datetime | None = Field(
        default=None, description="Filter roles created after this timestamp"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Filter roles created before this timestamp"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Filter roles updated after this timestamp"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Filter roles updated before this timestamp"
    )
