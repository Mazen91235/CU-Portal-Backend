from __future__ import annotations
from pydantic import BaseModel, Field


class UserEventRegisterDto(BaseModel):
    event_id: int = Field(..., gt=0, description="ID of the event to register for")


class UserEventUnregisterDto(BaseModel):
    event_id: int = Field(..., gt=0, description="ID of the event to unregister from")