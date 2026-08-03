from __future__ import annotations
from datetime import datetime
from typing import TypedDict, TYPE_CHECKING
from pydantic import BaseModel, EmailStr, Field
from .userDtos import UserResponseDto


if TYPE_CHECKING:
    from .baseDtos import BaseSearchDto
    from .facultyDtos import FacultyResponseDto
    from .departmentDtos import DepartmentResponseDto
    from .yearDtos import YearResponseDto

class SubjectCreateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Name of the subject")
    code: str = Field(
        ..., min_length=1, max_length=15, description="Unique code of the subject"
    )
    faculty_id: int = Field(..., gt=0, description="ID of the faculty this subject belongs to")
    department_id: int = Field(
        ..., gt=0, description="ID of the department this subject belongs to"
    )
    year_id: int = Field(..., gt=0, description="ID of the year this subject belongs to")
    credits: int = Field(..., gt=0, description="Number of credits for the subject")
    description: str | None = Field(
        None, max_length=1000, description="Description of the subject"
    )
    max_students: int | None = Field(
        None, gt=0, description="Maximum number of students allowed to register"
    )

class SubjectResponseDto(BaseModel):
    id: int = Field(..., description="ID of the subject")
    name: str = Field(..., description="Name of the subject")
    code: str | None = Field(None, description="Code of the subject")
    faculty: FacultyResponseDto | None = Field(None, description="Faculty associated with the subject")
    year: YearResponseDto | None = Field(None, description="Year associated with the subject")
    department: DepartmentResponseDto | None = Field(None, description="Department associated with the subject")
    details: dict | None = Field(None, description="Additional details about the subject")
    credits: int | None = Field(None, description="Number of credits for the subject")
    is_old: bool = Field(..., description="Whether this subject is deprecated/no longer offered")
    year_rank: int | None = Field(None, description="Rank/order of the subject within its year")
    term: int | None = Field(None, description="Term/semester the subject is offered in")
    users_count: int = Field(..., description="Number of users enrolled in the subject")
    users: list[UserResponseDto] | None = Field(None, description="info of enrolled users")

    model_config = {"from_attributes": True}

class SubjectUpdateDto(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Name of the subject")
    code: str = Field(..., min_length=1, max_length=15, description="Unique code of the subject")
    faculty_id: int = Field(..., gt=0, description="ID of the faculty this subject belongs to")
    department_id: int = Field(..., gt=0, description="ID of the department this subject belongs to")
    year_id: int = Field(..., gt=0, description="ID of the year this subject belongs to")
    credits: int = Field(..., gt=0, description="Number of credits for the subject")
    description: str | None = Field(None, max_length=1000, description="Description of the subject")
    max_students: int | None = Field(None, gt=0, description="Maximum number of students allowed to register")
    is_old: bool | None = Field(default=None, description="Whether the subject is deprecated")

class SubjectSearchDto(BaseSearchDto, BaseModel):
    id: int | None = Field(default=None, description="ID of Subject to filter by")
    faculty_id: int | None = Field(default=None, description="ID of Faculty to filter by")
    department_id: int | None = Field(default=None, description="ID of Department to filter by")
    year_id: int | None = Field(default=None, description="ID of Year to filter by")
    is_old: bool | None = Field(default=None, description="Whether the subject is deprecated")
    limit: int | None = Field(default=None, ge=1, le=100, description="Number of items per page for pagination")

class SubjectAvailableSearchDto(BaseModel):
    query: str | None = Field(default=None, description="Search query to filter available courses by name or code")

