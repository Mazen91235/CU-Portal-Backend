from __future__ import annotations
from datetime import datetime
from typing import Optional, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from .userDtos import UserResponseDto
    from .patientUserDtos import PatientUserResponseDto


class PatientRegisterDto:
    def __init__(self, name: str = ""):
        self.name = name

    def to_dict(self):
        return {"name": self.name}

    class Model(TypedDict):
        name: str


class PatientResponseDto:
    def __init__(
        self,
        id: int | None = None,
        name: str = "",
        token: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        user: UserResponseDto | None = None,
        patient_users: list[PatientUserResponseDto] | None = None,
    ):
        self.id = id
        self.name = name
        self.token = token
        self.created_at = created_at
        self.updated_at = updated_at
        self.user = user
        self.patient_users = patient_users

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "token": self.token,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.to_dict() if self.user else None,
            "patient_users": (
                [patient_user.to_dict() for patient_user in self.patient_users]
                if self.patient_users
                else []
            ),
        }

    class Model(TypedDict):
        id: int
        name: str
        token: str
        created_at: datetime
        updated_at: datetime
        user: Optional[UserResponseDto.Model]
        patient_users: list[PatientUserResponseDto.Model]


class PatientUpdateDto:
    def __init__(self, id: int | None = None, name: str = ""):
        self.id = id
        self.name = name

    def to_dict(self):
        return {"id": self.id, "name": self.name}

    class Model(TypedDict):
        id: int
        name: str


class PatientDeleteDto:
    def __init__(self, id: int | None = None):
        self.id = id

    class Model(TypedDict):
        id: int

    def to_dict(self):
        return {"id": self.id}


class PatientSearchDto:
    def __init__(
        self,
        id: int | None = None,
        name: str = "",
        token: str = "",
        user_id: int | None = None,
        created_at_from: str = "",
        created_at_to: str = "",
        updated_at_from: str = "",
        updated_at_to: str = "",
    ):
        self.id = id
        self.name = name
        self.token = token
        self.user_id = user_id
        self.created_at_from = created_at_from
        self.created_at_to = created_at_to
        self.updated_at_from = updated_at_from
        self.updated_at_to = updated_at_to

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "token": self.token,
            "user_id": self.user_id,
            "created_at_from": self.created_at_from,
            "created_at_to": self.created_at_to,
            "updated_at_from": self.updated_at_from,
            "updated_at_to": self.updated_at_to,
        }

    class Model(TypedDict):
        id: int
        name: str
        token: str
        user_id: int
        created_at_from: str
        created_at_to: str
        updated_at_from: str
        updated_at_to: str


class PatientLoginDto:
    def __init__(self, token: str = ""):
        self.token = token

    def to_dict(self):
        return {"token": self.token}

    class Model(TypedDict):
        token: str


class PatientLoginResponseDto:
    def __init__(
        self,
        id: int | None = None,
        name: str = "",
        token: str = "",
        refresh_token: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        user: UserResponseDto | None = None,
    ):
        self.id = id
        self.name = name
        self.token = token
        self.refresh_token = refresh_token
        self.created_at = created_at
        self.updated_at = updated_at
        self.user = user

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "token": self.token,
            "refresh_token": self.refresh_token,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.to_dict() if self.user else None,
        }

    class Model(TypedDict):
        id: int
        name: str
        token: str
        refresh_token: str
        created_at: datetime
        updated_at: datetime
        user: Optional[UserResponseDto.Model]
