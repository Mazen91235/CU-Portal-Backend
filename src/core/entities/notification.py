from __future__ import annotations
from enum import Enum
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
    AssociationProxy,
    association_proxy,
    TYPE_CHECKING,
    mapped_column,
    relationship,
    func,
)

if TYPE_CHECKING:
    from .user import User
    from .userNotification import UserNotification


class Notification(Base):
    # Tablename
    __tablename__ = "notifications"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(String(200), nullable=False)
    notification_type: Mapped[Optional[str]] = mapped_column(
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

    # Not Mapped
    @property
    def seen(self) -> Optional[bool]:
        return getattr(self, "_seen", None)

    @seen.setter
    def seen(self, value: Optional[bool]) -> None:
        setattr(self, "_seen", value)

    # Relationships
    users: AssociationProxy[set["User"]] = association_proxy(
        "user_notifications",
        "user",
        creator=lambda user: __import__(
            "core.entities.userNotification", fromlist=["UserNotification"]
        ).UserNotification(user=user),
    )
    user_notifications: Mapped[set["UserNotification"]] = relationship(
        "UserNotification",
        back_populates="notification",
        cascade="all, delete-orphan",
        collection_class=set,
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_notification_content_notification_type_parent_id",
            func.lower(content),
            "notification_type",
            "parent_id",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )

    # Attributes
    class NotificationType(str, Enum):
        TASK = "task"
        EXAM = "exam"
        ANNOUNCEMENT = "announcement"
        MATERIAL = "material"
        EVENT = "event"
