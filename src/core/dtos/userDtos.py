from __future__ import annotations
from datetime import datetime
from typing import TypedDict, TYPE_CHECKING
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from core.entities.user import User
    from core.dtos.facultyDtos import FacultyResponseDto
    from core.dtos.departmentDtos import DepartmentResponseDto
    from core.dtos.yearDtos import YearResponseDto
    from core.dtos.roleDtos import RoleResponseDto
    from core.dtos.pendingUserDtos import PendingUserResponseDto
    from core.dtos.materialDtos import MaterialResponseDto
    from core.dtos.taskDtos import TaskResponseDto
    from core.dtos.examDtos import ExamResponseDto
    from core.dtos.announcementDtos import AnnouncementResponseDto
    from core.dtos.notificationDtos import NotificationResponseDto
    from core.dtos.noteDtos import NoteResponseDto
    from core.dtos.logDtos import LogResponseDto
    from core.dtos.subjectDtos import SubjectResponseDto
    from core.dtos.eventDtos import EventResponseDto
    from core.dtos.attachmentDtos import AttachmentResponseDto

from core.dtos.baseDtos import BaseSearchDto


class UserCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=60, description="Name of User")
    email: EmailStr = Field(
        ..., min_length=1, max_length=100, description="Unique Email of User"
    )
    phone: str = Field(
        ..., min_length=1, max_length=13, description="Phone number of User"
    )
    gender: str = Field(..., min_length=1, max_length=6, description="Gender of User")
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
    details: dict = Field(
        default_factory=dict,
        description="Additional details about the user (stored as JSON like approval url, avatar, etc.)",
    )


class UserResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the user")
    name: str | None = Field(default=None, description="Name of User")
    email: EmailStr | None = Field(default=None, description="Email of User")
    phone: str | None = Field(default=None, description="Phone number of User")
    gender: str | None = Field(default=None, description="Gender of User")
    study_type: User.StudyType | None = Field(
        default=None, description="Study type of User"
    )
    section: int | None = Field(default=None, description="Section ID of the user")
    status: bool | None = Field(default=None, description="Status of the user")
    is_early_access: bool | None = Field(
        default=None, description="Whether the user is an early access user"
    )
    manages: dict | None = Field(
        default=None, description="Dictionary of items managed by this user"
    )
    details: dict | None = Field(
        default=None, description="Additional details about the user"
    )
    google_id: str | None = Field(default=None, description="Google ID of the user")
    google_name: str | None = Field(default=None, description="Google name of the user")
    google_email: EmailStr | None = Field(
        default=None, description="Google email of the user"
    )
    google_avatar: str | None = Field(
        default=None, description="Google avatar URL of the user"
    )
    created_at: datetime | None = Field(
        default=None, description="Creation Date of the user"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last Update Date of the user"
    )

    # Relationships
    year: YearResponseDto | None = Field(
        default=None, description="Year associated with the user"
    )
    department: DepartmentResponseDto | None = Field(
        default=None, description="Department associated with the user"
    )
    faculty: FacultyResponseDto | None = Field(
        default=None, description="Faculty associated with the user"
    )
    role: RoleResponseDto | None = Field(
        default=None, description="Role associated with the user"
    )
    pending_user: PendingUserResponseDto | None = Field(
        default=None, description="Pending user associated with the user (if any)"
    )
    materials: list[MaterialResponseDto] | None = Field(
        default=None, description="Materials associated with the user"
    )
    tasks: list[TaskResponseDto] | None = Field(
        default=None, description="Tasks associated with the user"
    )
    announcements: list[AnnouncementResponseDto] | None = Field(
        default=None, description="Announcements associated with the user"
    )
    notifications: list[NotificationResponseDto] | None = Field(
        default=None, description="Notifications associated with the user"
    )
    notes: list[NoteResponseDto] | None = Field(
        default=None, description="Notes associated with the user"
    )
    logs: list[LogResponseDto] | None = Field(
        default=None, description="Logs associated with the user"
    )
    subjects: list[SubjectResponseDto] | None = Field(
        default=None, description="Subjects associated with the user"
    )
    events: list[EventResponseDto] | None = Field(
        default=None, description="Events associated with the user"
    )
    avatar: AttachmentResponseDto | None = Field(
        default=None, description="Avatar attachment associated with the user"
    )
    attachments: list[AttachmentResponseDto] | None = Field(
        default=None, description="Attachments associated with the user"
    )
    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class UserUpdateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=60, description="Name of User")
    details: dict = Field(
        default_factory=dict,
        description="Additional details about the user (stored as JSON)",
    )


class UserSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of User to filter by")
    faculty_id: int | None = Field(
        default=None, description="ID of Faculty to filter by"
    )
    department_id: int | None = Field(
        default=None, description="ID of Department to filter by"
    )
    year_id: int | None = Field(default=None, description="ID of Year to filter by")
    status: bool | None = Field(default=None, description="Whether the user is active")


# User-Specific DTOs
class UserGetUserWithDetailsDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the user to retrieve")
    name: str | None = Field(default=None, description="Name of the user")
    email: EmailStr | None = Field(default=None, description="Email of the user")
    phone: str | None = Field(default=None, description="Phone number of the user")
    status: bool | None = Field(default=None, description="Status of the user")
    gender: str | None = Field(default=None, description="Gender of the user")
    section: int | None = Field(default=None, description="Section ID of the user")
    is_early_access: bool | None = Field(
        default=None, description="Whether the user is an early access user"
    )
    details: dict | None = Field(
        default=None, description="Additional details about the user"
    )
    google_id: str | None = Field(default=None, description="Google ID of the user")
    google_name: str | None = Field(default=None, description="Google name of the user")
    google_email: EmailStr | None = Field(
        default=None, description="Google email of the user"
    )
    google_avatar: str | None = Field(
        default=None, description="Google avatar URL of the user"
    )
    study_type: User.StudyType | None = Field(
        default=None, description="Study type of the user"
    )
    created_at: datetime | None = Field(
        default=None, description="Creation date of the user"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last update date of the user"
    )
    faculty: FacultyResponseDto | None = Field(
        default=None, description="Faculty associated with the user"
    )
    department: DepartmentResponseDto | None = Field(
        default=None, description="Department associated with the user"
    )
    year: YearResponseDto | None = Field(
        default=None, description="Year associated with the user"
    )
    role: RoleResponseDto | None = Field(
        default=None, description="Role associated with the user"
    )
    tasks_published: list[TaskResponseDto] | None = Field(
        default=None, description="Tasks published by the user"
    )
    tasks: list[TaskResponseDto] | None = Field(
        default=None, description="Tasks associated with the user"
    )
    exams_published: list[ExamResponseDto] | None = Field(
        default=None, description="Exams published by the user"
    )
    exams: list[ExamResponseDto] | None = Field(
        default=None, description="Exams associated with the user"
    )
    announcements_published: list[AnnouncementResponseDto] | None = Field(
        default=None, description="Announcements published by the user"
    )
    announcements: list[AnnouncementResponseDto] | None = Field(
        default=None, description="Announcements associated with the user"
    )
    materials: list[MaterialResponseDto] | None = Field(
        default=None, description="Materials associated with the user"
    )
    subjects: list[SubjectResponseDto] | None = Field(
        default=None, description="Subjects associated with the user"
    )
    events: list[EventResponseDto] | None = Field(
        default=None, description="Events associated with the user"
    )
    logs: list[LogResponseDto] | None = Field(
        default=None, description="Logs associated with the user"
    )
    avatar: AttachmentResponseDto | None = Field(
        default=None, description="Avatar attachment associated with the user"
    )


class UserSignUpResponseDto(BaseModel):
    token: str = Field(..., description="Verification token for the user")


class UserVerifyEmailDto(BaseModel):
    token: str = Field(..., description="Verification token for the user")


class UserGetStoredAccessTokenDto(BaseModel):
    google_details_token: str = Field(
        ..., description="Google details token for authentication"
    )
    oauth_state: str = Field(
        ..., description="OAuth state parameter for authentication"
    )


class UserLoginWithGoogleResponseDto(BaseModel):
    redirect_response_url: str = Field(
        ..., description="Redirect URL after Google login"
    )
    state: str = Field(..., description="State parameter for Google login")
    nonce: str = Field(..., description="Nonce parameter for Google login")


class UserLoginResponseDto(BaseModel):
    user: User | None = Field(default=None, description="Logged in user details")
    token: str | None = Field(
        default=None, description="Authentication token for the user"
    )
    state: str | None = Field(
        default=None, description="State parameter for google authentication"
    )
    token_expiration: int | None = Field(
        default=None, description="Token expiration time in seconds"
    )
    redirect_url: str | None = Field(
        default=None, description="Redirect URL after successful login"
    )
    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True,
    }


class UserTokenDetailsResponseDto(BaseModel):
    name: str = Field(..., description="Name of the user")
    email: EmailStr = Field(..., description="Email of the user")
    can_resend_after: float | None = Field(
        default=None,
        description="Time in seconds after which the user can resend the token",
    )


class UserResendTokenResponseDto(BaseModel):
    token: str = Field(..., description="New verification token for the user")


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
    study_type: User.StudyType | None = Field(
        None,
        description="New study type for the user (e.g., 'Mainstream', 'Credit')",
    )


class UserStatisticsResponseDto(BaseModel):
    users_count: int = Field(..., description="Total number of users")
    users_this_month_count: int = Field(
        ..., description="Number of users registered this month"
    )
    percentage_increase: float = Field(
        ..., description="Percentage increase in users compared to the previous month"
    )
    active_now_count: int = Field(..., description="Number of users currently active")
    pending_users_count: int = Field(
        ..., description="Number of users pending approval"
    )
    last_five_users_active: list[str] = Field(
        ..., description="List of Avatar URLs of the last five users who were active"
    )


class UserDeviceActionDto(BaseModel):
    device_id: UUID = Field(
        ..., description="Persistent unique identifier of the client device"
    )
    device_token: str = Field(..., min_length=1, description="Current FCM device token")
