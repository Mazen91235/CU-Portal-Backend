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
    from .event import Event


class UserEvent(Base):
    # Tablename
    __tablename__ = "user_events"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

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
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_event"),
        nullable=False,
    )
    user: Mapped["User"] = relationship("User", back_populates="user_events")
    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "events.id",
            ondelete="CASCADE",
            name="fk_event_user_event",
        ),
        nullable=False,
    )
    event: Mapped["Event"] = relationship("Event", back_populates="user_events")

    # Indexes
    __table_args__ = (
        Index("idx_user_event_user_id_event_id", "user_id", "event_id", unique=True),
    )
