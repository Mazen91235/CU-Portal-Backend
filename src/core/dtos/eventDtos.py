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
  from core.dtos.eventOrganizerDtos import EventOrganizerResponseDto
  from .baseDtos import BaseSearchDto


class EventCreateDto(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Title of the event" )
    start_date: datetime = Field(...,description="Start date of the event")
    end_date: datetime| None = Field(None,description="End date of the event")
    url: str | None = Field(default=None, max_length=100, description="URL of the event")
    price: float = Field(..., description="Price of the event")
    location_type: str = Field(..., description="Location type of the event e.g. online , offline")  
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
    event_organizer_id: int | None = Field(
            default=None, description="ID of Organizer of the event"
        )
    urls: list[str] = Field(
        default_factory=list, description="List of URLs"
    )
    links: dict[str, str] = Field(
        default_factory=dict, description="List of external links objects"
    )
    details: dict | None = Field(
        default=None, description="Additional details about the event"
    )

class EventResponseDto(BaseModel):
    id: int | None = Field(..., description="ID of the event")
    title: str | None = Field(..., description="Title of the event")
    start_date: datetime| None = Field(...,description="Start date of the event")
    end_date: datetime| None = Field(None,description="End date of the event")
    url: str| None = Field(..., description="Url of the event")
    price: float| None = Field(..., description="Price of the event")
    location_type: str| None = Field(..., description="Location type of the event e.g. online , offline")  
    location: str| None = Field(..., description="Location of the event")
    urls: list[str]| None = Field(default=None, description="List of event's file URLs")
    links: dict[str, str]| None = Field(default=None, description="List of external event's links")
    details: dict| None = Field(None,description="Additional details about the event")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    
    # Relationships
    author: UserResponseDto | None = Field(None, description="User who created the event")
    faculty: FacultyResponseDto | None = Field(None, description="Faculty associated with the event")
    department: DepartmentResponseDto | None = Field(None, description="Department associated with the event")
    year: YearResponseDto | None = Field(None, description="Year associated with the event")
    attendees: list[UserResponseDto] | None = Field(None, description="Attendees of the event")
    event_organizer:EventOrganizerResponseDto| None=Field(None, description="Organizer of the event")

    model_config = {
        "from_attributes": True,
    }

#make sure what will be edited in frontend
class EventUpdateDto(BaseModel):
    id: int = Field(..., description="ID of the event to update")
    title: str  = Field(..., min_length=1, max_length=100, description="Title of the event" )
    start_date: datetime = Field(...,description="Start date of the event")
    end_date: datetime| None = Field(None,description="End date of the event")
    price: float = Field(..., description="Price of the event")
    location: str = Field(..., description="Location of the event")
    location_type: str = Field(..., description="Location type of the event e.g. online , offline")  
    faculty_id: int | None = Field(
        default=None, description="ID of the faculty this event belongs to"
    )
    urls: list[str] = Field(
            default_factory=list, description="List of URLs"
        )
    links: dict[str, str] = Field(
        default_factory=dict, description="List of external links"
    )
    details: dict | None = Field(
        default=None, description="Additional details about the event"
    )


class EventSearchDto(BaseSearchDto, BaseModel):
    id: int | None = Field(
        default=None, description="ID of the event to filter by"
    )
    faculty_id: int | None = Field(default=None, description="Faculty ID to filter by")
    event_organizer_id: int | None = Field(
                default=None, description="ID of Event Organizer to filter by"
            )

class EventDeleteDto(BaseModel):
    id: int = Field(..., description="ID of Event to delete")
    faculty_id: int | None = Field(
            default=None, description="ID of the faculty this event belongs to"
        )
    department_id: int | None = Field(
            default=None, gt=0, description="ID of the department this event belongs to"
        )
    year_id: int | None = Field(
            default=None, description="ID of the year this event belongs to"
        )