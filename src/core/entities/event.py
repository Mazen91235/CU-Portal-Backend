from __future__ import annotations
from enum import Enum
from .base import (
    Base,
    Integer,
    Float,
    String,
    TIMESTAMP,
    datetime,
    JSON,
    MutableDict,
    MutableList,
    ForeignKey,
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
)

if TYPE_CHECKING:
    from .user import User
    from .userEvent import UserEvent
    from .faculty import Faculty
    from .department import Department
    from .year import Year
    from .eventOrganizer import EventOrganizer
    from .attachment import Attachment


class Event(Base):
    # Tablename
    __tablename__ = "events"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    location_type: Mapped["Event.LocationType"] = mapped_column(
        String(8), nullable=False
    )  # Online, Offline
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    urls: Mapped[list] = mapped_column(
        MutableList.as_mutable(JSON), nullable=True, default=list
    )
    links: Mapped[list[dict[str, str]]] = mapped_column(
        MutableList.as_mutable(JSON), nullable=True, default=list
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
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    author: Mapped["User"] = relationship("User", back_populates="events")
    faculty_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("faculties.id"), nullable=True
    )
    faculty: Mapped[Optional["Faculty"]] = relationship(
        "Faculty", back_populates="events"
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id"), nullable=True
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="events"
    )
    year_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("years.id"), nullable=True
    )
    year: Mapped[Optional["Year"]] = relationship("Year", back_populates="events")
    event_organizer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event_organizers.id"), nullable=False
    )
    event_organizer: Mapped["EventOrganizer"] = relationship(
        "EventOrganizer", back_populates="events"
    )
    attendees: AssociationProxy[list["User"]] = association_proxy(
        "user_events",
        "user",
        creator=lambda user: __import__(
            "core.entities.userEvent", fromlist=["UserEvent"]
        ).UserEvent(user=user),
    )
    user_events: Mapped[list["UserEvent"]] = relationship(
        "UserEvent",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    logo_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("attachments.id", ondelete="CASCADE", name="fk_attachment_event"),
        nullable=False,
    )
    logo: Mapped[Optional["Attachment"]] = relationship(
        "Attachment", back_populates="event_logo", foreign_keys=[logo_id]
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment",
        back_populates="event",
        cascade="all, delete-orphan",
        foreign_keys="Attachment.event_id",
    )

    # Indexes
    __table_args__ = (Index("idx_event_title", "title", unique=False),)

    # Attributes
    class LocationType(str, Enum):
        ONLINE = "Online"
        OFFLINE = "Offline"
