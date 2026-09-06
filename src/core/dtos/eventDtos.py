from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.entities.event import Event
    from core.dtos.userDtos import UserResponseDto
    from core.dtos.facultyDtos import FacultyResponseDto
    from core.dtos.departmentDtos import DepartmentResponseDto
    from core.dtos.yearDtos import YearResponseDto
    from core.dtos.attachmentDtos import AttachmentResponseDto
#   from core.dtos.eventOrganizerDtos import EventOrganizerResponseDto

from .baseDtos import BaseSearchDto


class EventCreateDto(BaseModel):
    title: str = Field(
        ..., min_length=1, max_length=100, description="Title of the event"
    )
    start_date: datetime = Field(..., description="Start date of the event")
    end_date: datetime | None = Field(None, description="End date of the event")
    price: float = Field(..., description="Price of the event")
    location_type: Event.LocationType = Field(
        ..., description="Location type of the event e.g. online , offline"
    )
    location: str = Field(..., description="Location of the event")
    faculty_id: int | None = Field(
        default=None, description="ID of the faculty this event belongs to"
    )
    department_id: int | None = Field(
        default=None, gt=0, description="ID of the department this event belongs to"
    )
    year_id: int | None = Field(
        default=None, description="ID of the year this event belongs to"
    )
    event_organizer_id: int = Field(..., description="ID of Organizer of the event")
    details: dict | None = Field(
        default=None,
        description="Additional details about the event (eg. url, urls, links, etc...)",
    )


class EventResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the event")
    title: str | None = Field(default=None, description="Title of the event")
    start_date: datetime | None = Field(
        default=None, description="Start date of the event"
    )
    end_date: datetime | None = Field(default=None, description="End date of the event")
    price: float | None = Field(default=None, description="Price of the event")
    location_type: Event.LocationType | None = Field(
        default=None, description="Location type of the event e.g. online , offline"
    )
    location: str | None = Field(default=None, description="Location of the event")
    details: dict | None = Field(
        default=None, description="Additional details about the event"
    )
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    # Relationships
    author: UserResponseDto | None = Field(
        default=None, description="User who created the event"
    )
    faculty: FacultyResponseDto | None = Field(
        default=None, description="Faculty associated with the event"
    )
    department: DepartmentResponseDto | None = Field(
        default=None, description="Department associated with the event"
    )
    year: YearResponseDto | None = Field(
        default=None, description="Year associated with the event"
    )
    attendees: list[UserResponseDto] | None = Field(
        default=None, description="Attendees of the event"
    )
    logo: AttachmentResponseDto | None = Field(
        default=None, description="Logo of the event"
    )
    attachments: list[AttachmentResponseDto] | None = Field(
        default=None, description="Attachments of the event"
    )
    # event_organizer: EventOrganizerResponseDto | None = Field(
    #     None, description="Organizer of the event"
    # )

    model_config = {
        "from_attributes": True,
    }


class EventUpdateDto(BaseModel):
    title: str = Field(
        ..., min_length=1, max_length=100, description="Title of the event"
    )
    start_date: datetime = Field(..., description="Start date of the event")
    end_date: datetime | None = Field(None, description="End date of the event")
    price: float = Field(..., description="Price of the event")
    location: str = Field(..., description="Location of the event")
    location_type: Event.LocationType = Field(
        ..., description="Location type of the event e.g. online , offline"
    )
    faculty_id: int | None = Field(
        default=None, description="ID of the faculty this event belongs to"
    )
    department_id: int | None = Field(
        default=None, gt=0, description="ID of the department this event belongs to"
    )
    year_id: int | None = Field(
        default=None, description="ID of the year this event belongs to"
    )
    event_organizer_id: int = Field(..., description="ID of Organizer of the event")
    details: dict | None = Field(
        default=None,
        description="Additional details about the event (eg. url, urls, links, etc...)",
    )


class EventDeleteDto(BaseModel):
    id: int = Field(..., description="ID of Event to delete")


class EventSearchDto(BaseSearchDto, BaseModel):
    id: int | None = Field(default=None, description="ID of the event to filter by")
    location_type: Event.LocationType | None = Field(
        default=None, description="Location type of the event to filter by"
    )
    faculty_id: int | None = Field(default=None, description="Faculty ID to filter by")
    department_id: int | None = Field(
        default=None, description="Department ID to filter by"
    )
    year_id: int | None = Field(default=None, description="Year ID to filter by")
    author_id: int | None = Field(default=None, description="Author ID to filter by")
    event_organizer_id: int | None = Field(
        default=None, description="ID of Event Organizer to filter by"
    )
    start_date_from: datetime | None = Field(
        default=None, description="Start date from to filter by"
    )
    start_date_to: datetime | None = Field(
        default=None, description="Start date to to filter by"
    )
    created_at_from: datetime | None = Field(
        default=None, description="Created at from to filter by"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Created at to to filter by"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Updated at from to filter by"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Updated at to to filter by"
    )
