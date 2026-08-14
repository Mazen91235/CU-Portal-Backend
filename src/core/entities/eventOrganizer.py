from __future__ import annotations

from .base import (
    Base,
    Integer,
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
    from .event import Event
    from .attachment import Attachment


class EventOrganizer(Base):
    # Tablename
    __tablename__ = "event_organizers"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    urls: Mapped[list] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=list
    )
    links: Mapped[dict[str, str]] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
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
    events: Mapped[list["Event"]] = relationship(
        "Event", back_populates="event_organizer", cascade="all, delete-orphan"
    )
    logo: Mapped[Optional["Attachment"]] = relationship(
        "Attachment",
        back_populates="event_organizer_logo",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="event_organizer", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("idx_event_organizer_name", "name", unique=True),)
