from __future__ import annotations

from .base import (
    Base,
    Integer,
    Boolean,
    TIMESTAMP,
    datetime,
    ForeignKey,
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
    from .notification import Notification


class UserNotification(Base):
    # Tablename
    __tablename__ = "user_notifications"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_notification"),
        nullable=False,
    )
    user: Mapped["User"] = relationship(
        "User", backref="user_notifications_associations"
    )
    notification_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "notifications.id",
            ondelete="CASCADE",
            name="fk_notification_user_notification",
        ),
        nullable=False,
    )
    notification: Mapped["Notification"] = relationship(
        "Notification", backref="user_notifications_associations"
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_notification_user_seen", "user_id", "seen"),
        Index("idx_user_notification_notification_seen", "notification_id", "seen"),
    )

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "seen": self.seen,
            "user_id": self.user_id,
            "notification_id": self.notification_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.to_dict() if self.user else None,
            "notification": self.notification.to_dict() if self.notification else None,
        }

    class Model(TypedDict):
        id: int
        seen: bool
        user_id: int
        notification_id: int
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        user: Optional[User.Model]
        notification: Optional[Notification.Model]
