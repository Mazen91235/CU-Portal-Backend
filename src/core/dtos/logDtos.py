from __future__ import annotations
from datetime import datetime
from typing import Optional, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from .userDtos import UserResponseDto
    from core.entities.logDetails import LogDetails


class LogResponseDto:
    def __init__(
        self,
        id: int | None = None,
        action: str = "",
        entity: str = "",
        level: str = "",
        code: int | None = None,
        message: str = "",
        source: str = "",
        path: str = "",
        ip: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        user: UserResponseDto | None = None,
        log_details: LogDetails | None = None,
    ):
        self.id = id
        self.action = action
        self.entity = entity
        self.level = level
        self.code = code
        self.message = message
        self.source = source
        self.path = path
        self.ip = ip
        self.created_at = created_at
        self.updated_at = updated_at
        self.user = user
        self.log_details = log_details

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "entity": self.entity,
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "source": self.source,
            "path": self.path,
            "ip": self.ip,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.to_dict() if self.user else None,
            "log_details": self.log_details.to_dict() if self.log_details else None,
        }

    class Model(TypedDict):
        id: int
        action: str
        entity: str
        level: str
        code: int
        message: str
        source: str
        path: str
        ip: str
        created_at: datetime
        updated_at: datetime
        user: Optional[UserResponseDto.Model]
        log_details: Optional[LogDetails.Model]


class LogSearchDto:
    def __init__(
        self,
        id: int | None = None,
        action: str = "",
        entity: str = "",
        level: str = "",
        code: int | None = None,
        source: str = "",
        path: str = "",
        ip: str = "",
        user_id: int | None = None,
        created_at_from: str = "",
        created_at_to: str = "",
        updated_at_from: str = "",
        updated_at_to: str = "",
    ):
        self.id = id
        self.action = action
        self.entity = entity
        self.level = level
        self.code = code
        self.source = source
        self.path = path
        self.ip = ip
        self.user_id = user_id
        self.created_at_from = created_at_from
        self.created_at_to = created_at_to
        self.updated_at_from = updated_at_from
        self.updated_at_to = updated_at_to

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "entity": self.entity,
            "level": self.level,
            "code": self.code,
            "source": self.source,
            "path": self.path,
            "ip": self.ip,
            "user_id": self.user_id,
            "created_at_from": self.created_at_from,
            "created_at_to": self.created_at_to,
            "updated_at_from": self.updated_at_from,
            "updated_at_to": self.updated_at_to,
        }

    class Model(TypedDict):
        id: int
        action: str
        entity: str
        level: str
        code: int
        source: str
        path: str
        ip: str
        user_id: int
        created_at_from: str
        created_at_to: str
        updated_at_from: str
        updated_at_to: str
