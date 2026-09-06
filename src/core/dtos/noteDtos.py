from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .userDtos import UserResponseDto

from .baseDtos import BaseSearchDto


class NoteCreateDto(BaseModel):
    title: str = Field(
        ..., min_length=1, max_length=100, description="Title of the note"
    )
    content: str = Field(..., max_length=500, description="Content of the note")
    date: datetime | None = Field(default=None, description="Date of the note")


class NoteResponseDto(BaseModel):
    id: int | None = Field(default=None, description="ID of the note")
    title: str | None = Field(default=None, description="Title of the note")
    content: str | None = Field(default=None, description="Content of the note")
    date: datetime | None = Field(default=None, description="Date of the note")

    created_at: datetime | None = Field(
        default=None, description="Creation Date of the note"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last Update Date of the note"
    )

    # Relationships
    author: UserResponseDto | None = Field(
        default=None, description="User who created the note"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class NoteUpdateDto(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Title of the note",
    )
    content: str = Field(
        ...,
        max_length=500,
        description="Content of the note",
    )
    date: datetime | None = Field(
        default=None,
        description="Date of the note",
    )


class NoteDeleteDto(BaseModel):
    id: int = Field(..., description="ID of the note to delete")


class NoteSearchDto(BaseSearchDto):
    id: int | None = Field(default=None, description="ID of the note to filter by")
    author_id: int | None = Field(default=None, description="ID of Author to filter by")
    date_from: datetime | None = Field(
        default=None, description="Filter notes created after this date"
    )
    date_to: datetime | None = Field(
        default=None, description="Filter notes created before this date"
    )
    created_at_from: datetime | None = Field(
        default=None, description="Filter notes created after this date"
    )
    created_at_to: datetime | None = Field(
        default=None, description="Filter notes created before this date"
    )
    updated_at_from: datetime | None = Field(
        default=None, description="Filter notes updated after this date"
    )
    updated_at_to: datetime | None = Field(
        default=None, description="Filter notes updated before this date"
    )
