from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Any
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .baseDtos import BaseSearchDto
    from .attachmentDtos import AttachmentResponseDto
    from .eventDtos import EventResponseDto


class EventOrganizerCreateDto(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Name of the event organizer",
    )
    url: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="logo URL of the event organizer",
    )
    urls: list[str] = Field(
        default_factory=list,
        description="List of associated URLs for the event organizer",
    )
    links: dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary of external links associated with the organizer",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details dictionary",
    )


class EventOrganizerResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the event organizer")
    name: str | None = Field(None, description="Name of the event organizer")
    url: str | None = Field(None, description="logo URL of the event organizer")
    urls: list[str] | None = Field(
        default_factory=list,
        description="List of associated Gooogle Drive URLs",
    )
    links: dict[str, str] | None = Field(
        default_factory=dict,
        description="Dictionary of external links",
    )
    details: dict | None = Field(
        default_factory=dict,
        description="Additional details dictionary",
    )
    created_at: datetime | None = Field(
        None, description="Creation date of the event organizer"
    )
    updated_at: datetime | None = Field(
        None, description="Last update date of the event organizer"
    )

    # Relationships
    events: list[EventResponseDto] | None = Field(
        default_factory=list,
        description="List of events organized by this organizer",
    )
    logo: AttachmentResponseDto | None = Field(
        None,
        description="Logo attachment associated with the organizer",
    )
    attachments: list[AttachmentResponseDto] | None = Field(
        default_factory=list,
        description="List of attachments associated with the organizer",
    )
    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class EventOrganizerUpdateDto(BaseModel):
    id: int = Field(..., description="ID of the event organizer to update")
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Name of the event organizer",
    )
    url: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="logo URL of the event organizer",
    )
    urls: list[str] = Field(
        default_factory=list,
        description="List of associated URLs for the event organizer",
    )
    links: dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary of external links associated with the organizer",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details dictionary",
    )


class EventOrganizerDeleteDto(BaseModel):
    id: int = Field(..., description="ID of the event organizer to delete")


class EventOrganizerSearchDto(BaseSearchDto, BaseModel):
    id: int | None = Field(
        default=None, description="ID of the event organizer to filter by"
    )
    name: str | None = Field(
        default=None, description="Name of the event organizer to filter by"
    )