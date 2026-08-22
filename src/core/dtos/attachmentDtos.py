from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class AttachmentResponseDto(BaseModel):
    id: int = Field(..., description="ID of the attachment")
    is_file: bool = Field(
        ..., description="Whether the attachment is a Drive file (True) or an external link (False)"
    )
    url: str = Field(..., description="URL of the attachment (Drive file or external link)")
    details: dict | None = Field(
        default=None, description="Additional metadata (e.g. file_data, link_title)"
    )
    author_id: int = Field(..., description="ID of the user whose Drive/account holds the file")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    # Pydantic Configuration
    model_config = {
        "from_attributes": True,
    }
