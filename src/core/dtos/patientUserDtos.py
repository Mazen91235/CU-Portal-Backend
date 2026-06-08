from __future__ import annotations
from datetime import datetime
from pgvector import Vector
from typing import Optional, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from .patientDtos import PatientResponseDto


class PatientUserRegisterDto:
    def __init__(
        self,
        name: str = "",
        relation: int | None = None,
        voice: str = "",
        img: str = "",
        img_vector: Vector | None = None,
    ):
        self.name = name
        self.relation = relation
        self.voice = voice
        self.img = img
        self.img_vector = img_vector

    def to_dict(self):
        return {
            "name": self.name,
            "relation": self.relation,
            "voice": self.voice,
            "img": self.img,
            "img_vector": (
                self.img_vector.to_text() if self.img_vector is not None else None
            ),
        }

    class Model(TypedDict):
        name: str
        relation: int
        voice: str
        img: str
        img_vector: Vector


class PatientUserResponseDto:
    def __init__(
        self,
        id: int | None = None,
        name: str = "",
        relation: int | None = None,
        voice: str = "",
        img: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        patient: PatientResponseDto | None = None,
    ):
        self.id = id
        self.name = name
        self.relation = relation
        self.voice = voice
        self.img = img
        self.created_at = created_at
        self.updated_at = updated_at
        self.patient = patient

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "relation": self.relation,
            "voice": self.voice,
            "img": self.img,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "patient": self.patient.to_dict() if self.patient else None,
        }

    class Model(TypedDict):
        id: int
        name: str
        relation: int
        voice: str
        img: str
        created_at: datetime
        updated_at: datetime
        patient: Optional[PatientResponseDto.Model]


class PatientUserDeleteDto:
    def __init__(self, id: int | None = None):
        self.id = id

    def to_dict(self):
        return {"id": self.id}

    class Model(TypedDict):
        id: int


class PatientUserSearchDto:
    def __init__(
        self,
        id: int | None = None,
        name: str = "",
        relation: int | None = None,
        img_vector: Vector | None = None,
        patient_id: int | None = None,
        created_at_from: str = "",
        created_at_to: str = "",
        updated_at_from: str = "",
        updated_at_to: str = "",
    ):
        self.id = id
        self.name = name
        self.relation = relation
        self.img_vector = img_vector
        self.patient_id = patient_id
        self.created_at_from = created_at_from
        self.created_at_to = created_at_to
        self.updated_at_from = updated_at_from
        self.updated_at_to = updated_at_to

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "relation": self.relation,
            "img_vector": (
                self.img_vector.to_text() if self.img_vector is not None else None
            ),
            "patient_id": self.patient_id,
            "created_at_from": self.created_at_from,
            "created_at_to": self.created_at_to,
            "updated_at_from": self.updated_at_from,
            "updated_at_to": self.updated_at_to,
        }

    class Model(TypedDict):
        id: int
        name: str
        relation: int
        img_vector: Vector
        patient_id: int
        created_at_from: str
        created_at_to: str
        updated_at_from: str
        updated_at_to: str
