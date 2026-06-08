from __future__ import annotations

from .base import (
    Base,
    Integer,
    String,
    TIMESTAMP,
    datetime,
    Index,
    Mapped,
    Optional,
    TimezoneHandler,
    TypedDict,
    TYPE_CHECKING,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from .user import User


class Notification(Base):
    # Tablename
    __tablename__ = "notifications"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # e.g., 'task', 'announcement', 'event'
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: TimezoneHandler.now("UTC"),
        nullable=True,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: TimezoneHandler.now("UTC"),
        onupdate=lambda: TimezoneHandler.now("UTC"),
        nullable=True,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", secondary="user_notifications", back_populates="notifications"
    )

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "type": self.type,
            "parent_id": self.parent_id,
            "url": self.url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "users": [user.to_dict() for user in self.users] if self.users else [],
        }

    class Model(TypedDict):
        id: int
        content: str
        type: Optional[str]
        parent_id: Optional[int]
        url: Optional[str]
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        users: list["User.Model"]
