from __future__ import annotations

from .base import (
    Base,
    Integer,
    Boolean,
    String,
    TIMESTAMP,
    datetime,
    JSON,
    MutableDict,
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
    from .pendingUser import PendingUser
    from .material import Material
    from .task import Task
    from .announcement import Announcement
    from .event import Event
    from .eventOrganizer import EventOrganizer


class Attachment(Base):
    # Tablename
    __tablename__ = "attachments"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_file: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )  # includes file_data, link_title
    author_google_refresh_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

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
    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_attachment"),
        nullable=False,
    )
    author: Mapped["User"] = relationship(
        "User", back_populates="attachments", cascade="all, delete-orphan"
    )
    pending_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "pending_users.id", ondelete="CASCADE", name="fk_pending_user_attachment"
        ),
        nullable=True,
    )
    pending_user: Mapped[Optional["PendingUser"]] = relationship(
        "PendingUser", back_populates="attachment", cascade="all, delete-orphan"
    )
    material_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE", name="fk_material_attachment"),
        nullable=True,
    )
    material: Mapped[Optional["Material"]] = relationship(
        "Material", back_populates="attachment", cascade="save-update, merge"
    )
    task_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE", name="fk_task_attachment"),
        nullable=True,
    )
    task: Mapped[Optional["Task"]] = relationship(
        "Task", back_populates="attachments", cascade="save-update, merge"
    )
    announcement_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "announcements.id", ondelete="CASCADE", name="fk_announcement_attachment"
        ),
        nullable=True,
    )
    announcement: Mapped[Optional["Announcement"]] = relationship(
        "Announcement", back_populates="attachments", cascade="save-update, merge"
    )
    event_logo_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE", name="fk_event_logo_attachment"),
        nullable=True,
    )
    event_logo: Mapped[Optional["Event"]] = relationship(
        "Event", back_populates="logo", cascade="save-update, merge"
    )
    event_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE", name="fk_event_attachment"),
        nullable=True,
    )
    event: Mapped[Optional["Event"]] = relationship(
        "Event", back_populates="attachments", cascade="save-update, merge"
    )
    event_organizer_logo_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "event_organizers.id",
            ondelete="CASCADE",
            name="fk_event_organizer_logo_attachment",
        ),
        nullable=True,
    )
    event_organizer_logo: Mapped[Optional["EventOrganizer"]] = relationship(
        "EventOrganizer", back_populates="logo", cascade="save-update, merge"
    )
    event_organizer_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "event_organizers.id",
            ondelete="CASCADE",
            name="fk_event_organizer_attachment",
        ),
        nullable=True,
    )
    event_organizer: Mapped[Optional["EventOrganizer"]] = relationship(
        "EventOrganizer", back_populates="attachments", cascade="save-update, merge"
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_attachment_author_id",
            "author_id",
        ),
    )
