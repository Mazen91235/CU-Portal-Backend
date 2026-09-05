from __future__ import annotations
from typing import TYPE_CHECKING, Literal
from datetime import datetime
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.dtos.noteDtos import NoteResponseDto
    from core.dtos.eventDtos import EventResponseDto

from core.dtos.baseDtos import BaseSearchDto


class CalendarResponseDto(BaseModel):
    events: dict[str, CalendarDayDto] = Field(
        default_factory=dict, description="Dictionary of events grouped by date"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class CalendarDayDto(BaseModel):
    tasks: list[CalendarDayEventDto] = Field(
        default_factory=list, description="List of tasks for the day"
    )
    exams: list[CalendarDayEventDto] = Field(
        default_factory=list, description="List of exams for the day"
    )
    announcements: list[CalendarDayEventDto] = Field(
        default_factory=list, description="List of announcements for the day"
    )
    events: list[EventResponseDto] = Field(
        default_factory=list, description="List of events for the day"
    )
    notes: list[NoteResponseDto] = Field(  # Should be NoteResponseDto
        default_factory=list, description="List of notes for the day"
    )


class CalendarDayEventDto(BaseModel):
    id: int | None = Field(..., description="Unique identifier for the event")
    event_type: Literal["assignment", "exam", "announcement"] = Field(
        ..., description="Type of the event (task, exam, announcement)"
    )
    title: str = Field(..., description="Title of the event")
    subject: str | None = Field(
        default=None, description="Subject of the event (if applicable)"
    )
    due: str | None = Field(
        default=None, description="Due date of the event (if applicable)"
    )
    location: str | None = Field(
        default=None, description="Location of the event (if applicable)"
    )


class CalendarSearchDto(BaseSearchDto):
    date_from: datetime | None = Field(
        default=None, description="Start date for the calendar search"
    )
    date_to: datetime | None = Field(
        default=None, description="End date for the calendar search"
    )
