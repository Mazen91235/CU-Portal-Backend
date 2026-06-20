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
    url: str | None = Field(
        None, max_length=255, description="URL of User Approval Image (if any)"
    )
    is_early_access: bool = Field(
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
    id: int | None = Field(None, description="ID of the user")
    name: str = Field(..., description="Name of User")
    email: EmailStr = Field(..., description="Email of User")
    phone: str = Field(..., description="Phone number of User")
    gender: str = Field(..., description="Gender of User")
    type: User.Type = Field(..., description="Type of User")
    section: int | None = Field(None, description="Section ID of the user")
    status: bool | None = Field(None, description="Status of the user")
    is_early_access: bool | None = Field(
        None, description="Whether the user is an early access user"
    )
    manages: dict | None = Field(
        None, description="Dictionary of items managed by this user"
    )
    details: dict | None = Field(None, description="Additional details about the user")
    google_id: str = Field("", description="Google ID of the user")
    google_name: str = Field("", description="Google name of the user")
    google_email: EmailStr = Field("", description="Google email of the user")
    google_avatar: str = Field("", description="Google avatar URL of the user")
    created_at: datetime | None = Field(None, description="Creation Date of the user")
    updated_at: datetime | None = Field(
        None, description="Last Update Date of the user"
    )

    # Relationships
    year: YearResponseDto | None = Field(
        None, description="Year associated with the user"
    )
    department: DepartmentResponseDto | None = Field(
        None, description="Department associated with the user"
    )
    faculty: FacultyResponseDto | None = Field(
        None, description="Faculty associated with the user"
    )
    role: RoleResponseDto | None = Field(
        None, description="Role associated with the user"
    )
    pending_user: PendingUserResponseDto | None = Field(
        None, description="Pending user associated with the user (if any)"
    )
    materials: list[MaterialResponseDto] | None = Field(
        None, description="Materials associated with the user"
    )
    tasks: list[TaskResponseDto] | None = Field(
        None, description="Tasks associated with the user"
    )
    announcements: list[AnnouncementResponseDto] | None = Field(
        None, description="Announcements associated with the user"
    )
    notifications: list[NotificationResponseDto] | None = Field(
        None, description="Notifications associated with the user"
    )
    logs: list[LogResponseDto] | None = Field(
        None, description="Logs associated with the user"
    )
    subjects: list[SubjectResponseDto] | None = Field(
        None, description="Subjects associated with the user"
    )

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
class UserLoginResponseDto(BaseModel):
    user: UserResponseDto = Field(..., description="Logged in user details")
    token: str = Field(..., description="Authentication token for the user")


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
