from __future__ import annotations
from pydantic import BaseModel, Field


class UserSubjectLinkActionDto(BaseModel):
    subject_id: int = Field(
        ...,
        gt=0,
        description="ID of the subject to perform action on (register/unregister)",
    )
