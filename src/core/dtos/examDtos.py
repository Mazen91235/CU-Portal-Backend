from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field
from core.dtos.baseDtos import BaseSearchDto

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto
   #from core.dtos.subjectDtos import SubjectResponseDto
   #from core.dtos.facultyDtos import FacultyResponseDto
   #from core.dtos.departmentDtos import DepartmentResponseDto
   #from core.dtos.yearDtos import YearResponseDto
   # TODO: Uncomment the above lines and implement the corresponding DTOs for Subject, Faculty, Department, and Year when they are available.


class ExamCreateDto(BaseModel):
    title: str = Field(..., min_length=1, max_length=60, description="Title of the Exam")
    description: str | None = Field(None, description="Detailed description of the exam")
    instructions: str | None = Field(None, description="Specific instructions for the exam")
    due_date: str = Field(..., description="Date of the exam (YYYY-MM-DD)")
    start_time: str = Field(..., description="Start time of the exam (HH:MM:SS)")
    location: str | None = Field(None, max_length=100, description="Location of the exam")
    duration: float | None = Field(None, gt=0, description="Duration in hours or minutes")
    exam_type: str = Field(..., min_length=1, description="Type of the exam (e.g., Midterm, Final)")
    exam_format: str | None = Field(None, description="Format of the exam (e.g., MCQ, Essay)")
    exam_weight: str | None = Field(None, description="Weight/Grade percentage of the exam")
    subject_id: int = Field(..., gt=0, description="ID of the subject this exam belongs to")


class ExamUpdateDto(BaseModel):
    title: str = Field(..., min_length=1, max_length=60, description="Title of the Exam")
    description: str | None = Field(None, description="Detailed description of the exam")
    instructions: str | None = Field(None, description="Specific instructions for the exam")
    due_date: str = Field(..., description="Date of the exam (YYYY-MM-DD)")
    start_time: str = Field(..., description="Start time of the exam (HH:MM:SS)")
    location: str | None = Field(None, max_length=100, description="Location of the exam")
    duration: float | None = Field(None, gt=0, description="Duration in hours or minutes")
    exam_type: str = Field(..., min_length=1, description="Type of the exam (e.g., Midterm, Final)")
    exam_format: str | None = Field(None, description="Format of the exam (e.g., MCQ, Essay)")
    exam_weight: str | None = Field(None, description="Weight/Grade percentage of the exam")
    subject_id: int = Field(..., gt=0, description="ID of the subject this exam belongs to")


class ExamSearchDto(BaseSearchDto):
    subject_id: int | None = Field(None, gt=0, description="ID of Subject to filter by")
    faculty_id: int | None = Field(None, gt=0, description="ID of Faculty to filter by")
    department_id: int | None = Field(None, gt=0, description="ID of Department to filter by")
    year_id: int | None = Field(None, gt=0, description="ID of Year to filter by")
    author_id: int | None = Field(None, gt=0, description="ID of Author to filter by")
    start_date: str | None = Field(None, description="Start date for deadline filter (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date for deadline filter (YYYY-MM-DD)")


class ExamResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the task/exam")
    name: str | None = Field(None, description="Title of the exam")
    type: str | None = Field(None, description="Type of task (will always be 'exam')")
    urls: list[str] | None = Field(None, description="URLs associated with the exam")
    links: list[str] | None = Field(None, description="Links associated with the exam")
    url: str | None = Field(None, description="Main URL of the exam")
    details: dict | None = Field(None, description="JSON details (description, duration, etc.)")
    deadline: datetime | None = Field(None, description="Exact Datetime deadline")
    due_date: datetime | None = Field(None, description="Date of the exam")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last updated timestamp")

    # Relationships
    subject: SubjectResponseDto | None = Field(None, description="Subject of the exam")
    author: UserResponseDto | None = Field(None, description="Author of the exam")
    faculty: FacultyResponseDto | None = Field(None, description="Faculty of the exam")
    department: DepartmentResponseDto | None = Field(None, description="Department of the exam")
    year: YearResponseDto | None = Field(None, description="Year of the exam")

    model_config = {
        "from_attributes": True,
    }