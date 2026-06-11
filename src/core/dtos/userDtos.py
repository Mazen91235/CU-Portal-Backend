from __future__ import annotations
from datetime import datetime
from typing import TypedDict, TYPE_CHECKING
from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from .baseDtos import BaseSearchDto
    from core.entities.user import User


class UserRegisterDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=60, description="Name of User")
    email: EmailStr = Field(
        ..., min_length=1, max_length=100, description="Unique Email of User"
    )
    phone: str = Field(
        ..., min_length=1, max_length=13, description="Phone number of User"
    )
    gender: str = Field(..., min_length=1, max_length=6, description="Gender of User")
    early_access: bool = Field(
        default=False, description="Whether the user is an early access user"
    )
    agreed: bool = Field(
        default=False, description="Whether the user agreed to terms and conditions"
    )
    google_details_token: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Google details token for authentication",
    )


class UserResponseDto(BaseModel):
    id: int | None = None
    name: str = ""
    email: EmailStr = ""
    phone: str = ""
    gender: str = ""
    type: User.Type = User.Type.MAINSTREAM
    section: int | None = None
    status: bool | None = None
    is_early_access: bool | None = None
    manages: dict | None = None
    details: dict | None = None
    google_id: str = ""
    google_name: str = ""
    google_email: EmailStr = ""
    google_avatar: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Relationships
    year: YearResponseDto | None = None
    department: DepartmentResponseDto | None = None
    faculty: FacultyResponseDto | None = None
    role: RoleResponseDto | None = None
    pending_user: PendingUserResponseDto | None = None
    materials: list[MaterialResponseDto] | None = None
    tasks: list[TaskResponseDto] | None = None
    announcements: list[AnnouncementResponseDto] | None = None
    notifications: list[NotificationResponseDto] | None = None
    logs: list[LogResponseDto] | None = None
    subjects: list[SubjectResponseDto] | None = None

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class UserUpdateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=60, description="Name of User")
    url: str = Field(..., min_length=1, max_length=255, description="URL of User")


class UserSearchDto(BaseSearchDto, BaseModel):
    faculty_id: int | None = Field(None, description="ID of Faculty to filter by")
    department_id: int | None = Field(None, description="ID of Department to filter by")
    year_id: int | None = Field(None, description="ID of Year to filter by")
    is_active: bool | None = Field(None, description="Whether the user is active")


# User-Specific DTOs
class UserUpdateUsersRecordDto(BaseModel):
    id: int = Field(..., description="ID of the user to update")
    approved: bool = Field(True, description="Whether the user is approved")
    role_id: int | None = Field(None, description="ID of the new role for the user")


class UserUpdateUsersDto(BaseModel):
    data_to_update: list[UserUpdateUsersRecordDto] = Field(
        ..., description="List of user records to update"
    )


class UserHasPermissionsDto(BaseModel):
    required_permissions: list[str] = Field(
        ..., description="List of permissions to check for the user"
    )
    is_and: bool = Field(
        default=True,
        description="Whether the user needs to have all permissions (AND) or at least one (OR)",
    )


class UserUpdateAcademicDataDto(BaseModel):
    faculty_id: int | None = Field(
        None, description="ID of the new faculty for the user"
    )
    department_id: int | None = Field(
        None, description="ID of the new department for the user"
    )
    year_id: int | None = Field(None, description="ID of the new year for the user")
    study_type: User.Type | None = Field(
        None,
        description="New study type for the user (e.g., 'undergraduate', 'graduate')",
    )
