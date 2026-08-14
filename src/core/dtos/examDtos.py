from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field
from core.dtos.baseDtos import BaseSearchDto

if TYPE_CHECKING:
    from core.dtos.userDtos import UserResponseDto
    from core.dtos.subjectDtos import SubjectResponseDto
    from core.dtos.facultyDtos import FacultyResponseDto
    from core.dtos.departmentDtos import DepartmentResponseDto
    from core.dtos.yearDtos import YearResponseDto


class ExamCreateDto(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=60, description="Title or name of the exam"
    )
    deadline: datetime = Field(..., description="Datetime for the exam deadline")
    subject_id: int = Field(
        ..., gt=0, description="ID of the subject this exam belongs to"
    )
    faculty_id: int | None = Field(
        default=None, description="ID of the faculty this task belongs to"
    )
    department_id: int | None = Field(
        default=None, gt=0, description="ID of the department this task belongs to"
    )
    year_id: int | None = Field(
        default=None, description="ID of the year this task belongs to"
    )
    details: dict | None = Field(
        default=None,
        description="Additional details about the exam",
    )
    # description, instructions, location, duration, exam_type, exam_format, exam_weight all are in details field


class ExamResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the task/exam")
    name: str | None = Field(None, description="Title of the exam")
    type: str | None = Field(None, description="Type of task (will always be 'exam')")
    deadline: datetime | None = Field(None, description="Exact Datetime deadline")
    due_date: datetime | None = Field(None, description="Date of the exam")
    details: dict | None = Field(
        None,
        description="JSON details (description, instructions, location, duration, exam_type, exam_format, exam_weight, etc.)",
    )
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last updated timestamp")

    # Relationships
    subject: SubjectResponseDto | None = Field(None, description="Subject of the exam")
    author: UserResponseDto | None = Field(None, description="Author of the exam")
    faculty: FacultyResponseDto | None = Field(None, description="Faculty of the exam")
    department: DepartmentResponseDto | None = Field(
        None, description="Department of the exam"
    )
    year: YearResponseDto | None = Field(None, description="Year of the exam")

    model_config = {
        "from_attributes": True,
    }


class ExamUpdateDto(BaseModel):
    id: int = Field(..., description="ID of the exam to update")
    name: str | None = Field(
        None, min_length=1, max_length=60, description="Title of the exam"
    )
    deadline: datetime | None = Field(None, description="Datetime deadline of the exam")
    subject_id: int = Field(
        ..., gt=0, description="ID of the subject this exam belongs to"
    )
    details: dict | None = Field(
        None,
        description="Additional details about the exam",
    )


class ExamDeleteDto(BaseModel):
    id: int = Field(..., description="ID of the exam to delete")


class ExamSearchDto(BaseSearchDto):
    id: int | None = Field(None, gt=0, description="ID of Exam to filter by")
    subject_id: int | None = Field(None, gt=0, description="ID of Subject to filter by")
    faculty_id: int | None = Field(None, gt=0, description="ID of Faculty to filter by")
    department_id: int | None = Field(
        None, gt=0, description="ID of Department to filter by"
    )
    year_id: int | None = Field(None, gt=0, description="ID of Year to filter by")
    author_id: int | None = Field(None, gt=0, description="ID of Author to filter by")
    deadline_from: datetime | None = Field(
        None, description="Filter exams with deadline after this datetime"
    )
    deadline_to: datetime | None = Field(
        None, description="Filter exams with deadline before this datetime"
    )
    created_at_from: datetime | None = Field(
        None, description="Filter exams created after this datetime"
    )
    created_at_to: datetime | None = Field(
        None, description="Filter exams created before this datetime"
    )
    updated_at_from: datetime | None = Field(
        None, description="Filter exams updated after this datetime"
    )
    updated_at_to: datetime | None = Field(
        None, description="Filter exams updated before this datetime"
    )
