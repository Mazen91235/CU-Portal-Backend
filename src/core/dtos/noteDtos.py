from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .baseDtos import BaseSearchDto
    from .userDtos import UserResponseDto


class NoteCreateDto(BaseModel):
    content: str = Field(
        ..., min_length=1, max_length=500, description="Content of the note"
    )
    date: datetime | None = Field(None, description="Due date of the note")


class NoteResponseDto(BaseModel):
    id: int | None = Field(None, description="ID of the note")
    content: str | None = Field(None, description="Content of the note")
    date: datetime | None = Field(None, description="Due date of the note")

    updated_at: datetime | None = Field(
        None, description="Last Update Date of the note"
    )

    created_at: datetime | None = Field(None, description="Creation Date of the note")

    # Relationships
    author: UserResponseDto | None = Field(
        None, description="User who created the note"
    )

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }


class NoteUpdateDto(BaseModel):
    content: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Content of the note",
    )
    date: datetime | None = Field(
        None,
        description="Date of the note",
    )


class NoteDeleteDto(BaseModel):
    id: int = Field(..., description="ID of the note to delete")


class NoteSearchDto(BaseSearchDto, BaseModel):
    content: str | None = Field(default=None, description="Content of the note")
    author_id: int | None = Field(default=None, description="ID of Author to filter by")
    date: datetime | None = Field(
        None,
        description="Date of the note",
    )
