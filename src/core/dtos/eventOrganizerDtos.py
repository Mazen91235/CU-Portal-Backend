from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .attachmentDtos import AttachmentResponseDto
    from .eventDtos import EventResponseDto

from .baseDtos import BaseSearchDto


class EventOrganizerCreateDto(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Name of the event organizer",
    )
    details: dict = Field(
        default_factory=dict,
        description="Additional details dictionary (eg. url, urls, links, etc...)",
    )


class EventOrganizerResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the event organizer")
    name: str | None = Field(default=None, description="Name of the event organizer")
    details: dict | None = Field(
        default=None,
        description="Additional details dictionary",
    )
    created_at: datetime | None = Field(
        default=None, description="Creation date of the event organizer"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last update date of the event organizer"
    )

    # Relationships
    events: list[EventResponseDto] | None = Field(
        default=None,
        description="List of events organized by this organizer",
    )
    logo: AttachmentResponseDto | None = Field(
        default=None,
        description="Logo attachment associated with the organizer",
    )
    attachments: list[AttachmentResponseDto] | None = Field(
        default=None,
        description="List of attachments associated with the organizer",
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class EventOrganizerUpdateDto(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Name of the event organizer",
    )
    details: dict = Field(
        default_factory=dict,
        description="Additional details dictionary (eg. url, urls, links, etc...)",
    )


class EventOrganizerDeleteDto(BaseModel):
    id: int = Field(..., description="ID of the event organizer to delete")


class EventOrganizerSearchDto(BaseSearchDto):
    id: int | None = Field(
        default=None, description="ID of the event organizer to filter by"
    )
    created_at_from: datetime | None = Field(
        default=None, description="Filter event organizers created after this date"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Filter event organizers created before this date"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Filter event organizers updated after this date"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Filter event organizers updated before this date"
    )
