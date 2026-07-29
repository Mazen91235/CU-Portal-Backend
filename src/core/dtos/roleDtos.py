from __future__ import annotations
from datetime import datetime
from typing import TypedDict, TYPE_CHECKING
from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from core.entities.user import User
    from .baseDtos import BaseSearchDto


class AddRoleDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=60, description="Name of Role")
    permissions: list[str] | None = Field(
        None, description="List of permissions associated with the role"
    )


class RoleResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the role")
    name: str = Field(..., description="Name of Role")
    permissions: list[str] | None = Field(
        None, description="List of permissions associated with the role"
    )
    permission_count: int | None = Field(
        None, description="Count of permissions associated with the role"
    )
    level: int | None = Field(None, description="Level of the role")
    users_count: int | None = Field(
        None, description="Count of users associated with the role"
    )

class updateRoleDto(BaseModel):
    id: int | None = Field(None, description="ID of the role to update")
    name: str | None = Field(None, min_length=1, max_length=60, description="Name of Role")
    permissions: list[str] | None = Field(
        None, description="List of permissions associated with the role"
    )


class RoleSearchDto(BaseModel):
    id: int | None = Field(None, description="ID of the role")
    name: str | None = Field(None, description="Name of the role")
