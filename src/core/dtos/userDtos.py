from __future__ import annotations
from datetime import datetime
from typing import TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities.user import User
    from core.entities.token import Token
    from .patientDtos import PatientResponseDto
    from .logDtos import LogResponseDto


class UserRegisterDto:
    def __init__(self, name: str = "", email: str = "", password: str = ""):
        self.name = name
        self.email = email
        self.password = password

    def to_dict(self):
        return {"name": self.name, "email": self.email, "password": self.password}

    class Model(TypedDict):
        name: str
        email: str
        password: str


class UserResponseDto:
    def __init__(
        self,
        id: int | None = None,
        name: str = "",
        email: str = "",
        is_verified: bool | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        tokens: list[Token] | None = None,
        patients: list[PatientResponseDto] | None = None,
        logs: list[LogResponseDto] = [],
    ):
        self.id = id
        self.name = name
        self.email = email
        self.is_verified = is_verified
        self.created_at = created_at
        self.updated_at = updated_at
        self.tokens = tokens
        self.patients = patients
        self.logs = logs

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tokens": [token.to_dict() for token in self.tokens] if self.tokens else [],
            "patients": (
                [patient.to_dict() for patient in self.patients]
                if self.patients
                else []
            ),
            "logs": [log.to_dict() for log in self.logs] if self.logs else [],
        }

    class Model(TypedDict):
        id: int
        name: str
        email: str
        is_verified: bool
        created_at: datetime
        updated_at: datetime
        tokens: list[Token.Model]
        patients: list[PatientResponseDto.Model]
        logs: list[LogResponseDto.Model]


class UserUpdateDto:
    def __init__(self, name: str = ""):
        self.name = name

    def to_dict(self):
        return {"name": self.name}

    class Model(TypedDict):
        name: str


class UserSearchDto:
    def __init__(
        self,
        id: int | None = None,
        name: str = "",
        email: str = "",
        is_verified: bool | None = None,
        created_at_from: str = "",
        created_at_to: str = "",
        updated_at_from: str = "",
        updated_at_to: str = "",
    ):
        self.id = id
        self.name = name
        self.email = email
        self.is_verified = is_verified
        self.created_at_from = created_at_from
        self.created_at_to = created_at_to
        self.updated_at_from = updated_at_from
        self.updated_at_to = updated_at_to

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_verified": self.is_verified,
            "created_at_from": self.created_at_from,
            "created_at_to": self.created_at_to,
            "updated_at_from": self.updated_at_from,
            "updated_at_to": self.updated_at_to,
        }

    class Model(TypedDict):
        id: int
        name: str
        email: str
        is_verified: bool
        created_at_from: str
        created_at_to: str
        updated_at_from: str
        updated_at_to: str


class UserLoginDto:
    def __init__(self, email: str = "", password: str = ""):
        self.email = email
        self.password = password

    def to_dict(self):
        return {"email": self.email, "password": self.password}

    class Model(TypedDict):
        email: str
        password: str


class UserLoginResponseDto:
    def __init__(self, user: User | None = None, token: str = ""):
        self.user = user
        self.token = token

    def to_dict(self):
        return {"user": self.user.to_dict() if self.user else None, "token": self.token}

    class Model(TypedDict):
        user: User.Model
        token: str


class UserVerifyEmailDto:
    def __init__(self, token: str = ""):
        self.token = token

    def to_dict(self):
        return {"token": self.token}

    class Model(TypedDict):
        token: str


class UserForgotPasswordDto:
    def __init__(self, email: str = ""):
        self.email = email

    def to_dict(self):
        return {"email": self.email}

    class Model(TypedDict):
        email: str


class UserResetPasswordDto:
    def __init__(self, token: str = "", new_password: str = ""):
        self.token = token
        self.new_password = new_password

    def to_dict(self):
        return {"token": self.token, "new_password": self.new_password}

    class Model(TypedDict):
        token: str
        new_password: str


class UserChangePasswordDto:
    def __init__(self, old_password: str = "", new_password: str = ""):
        self.old_password = old_password
        self.new_password = new_password

    def to_dict(self):
        return {"old_password": self.old_password, "new_password": self.new_password}

    class Model(TypedDict):
        old_password: str
        new_password: str


class UserResendTokenDto:
    def __init__(self, email: str = ""):
        self.email = email

    def to_dict(self):
        return {"email": self.email}

    class Model(TypedDict):
        email: str
