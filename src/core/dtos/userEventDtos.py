from __future__ import annotations
from pydantic import BaseModel, Field


class UserEventActionDto(BaseModel):
    event_id: int = Field(..., gt=0, description="ID of the event to action on")
