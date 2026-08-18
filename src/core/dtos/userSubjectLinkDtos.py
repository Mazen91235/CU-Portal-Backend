from __future__ import annotations
from pydantic import BaseModel, Field
  

class UserSubjectLinkRegisterDto(BaseModel):
    subject_id: int = Field(..., gt=0, description="ID of the subject to register for")


class UserSubjectLinkUnregisterDto(BaseModel):
    subject_id: int = Field(..., gt=0, description="ID of the subject to unregister from")


