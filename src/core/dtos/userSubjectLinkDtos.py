from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
       

class UserSubjectLinkRegisterDto(BaseModel):
    subject_id: int = Field(..., gt=0, description="ID of the subject to register for")


class UserSubjectLinkUnregisterDto(BaseModel):
    subject_id: int = Field(..., gt=0, description="ID of the subject to unregister from")


class SubjectEnrolledResponseDto(BaseModel):
    id: int = Field(..., description="ID of the subject")
    name: str = Field(..., description="Name of the subject")
    code: str | None = Field(None, description="Code of the subject")
    faculty: FacultyMinResponseDto | None = Field(None, description="Faculty associated with the subject")
    department: DepartmentMinResponseDto | None = Field(None, description="Department associated with the subject")
    year: YearMinResponseDto | None = Field(None, description="Year associated with the subject")
    details: dict | None = Field(None, description="Additional details about the subject")
    credits: int | None = Field(None, description="Number of credits for the subject")
    is_old: bool = Field(..., description="Whether this subject is deprecated/no longer offered")
    year_rank: int | None = Field(None, description="Rank/order of the subject within its year")
    term: int | None = Field(None, description="Term/semester the subject is offered in")

    model_config = {"from_attributes": True}


class UserSubjectLinkResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the link")
    user_id: int = Field(..., description="ID of the user")
    subject_id: int = Field(..., description="ID of the subject")
    created_at: datetime | None = Field(None, description="When the user registered for the subject")
    updated_at: datetime | None = Field(None, description="Last update time of the link")

    model_config = {"from_attributes": True}
