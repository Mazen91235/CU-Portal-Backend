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
    from .user import User
    from .subject import Subject
    from .task import Task
    from .announcement import Announcement
    from .event import Event
    from .week import Week


class Year(Base):
    # Tablename
    __tablename__ = "years"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
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
    users: Mapped[set["User"]] = relationship(
        "User", back_populates="year", cascade="all, delete-orphan", collection_class=set
    )
    subjects: Mapped[set["Subject"]] = relationship(
        "Subject", back_populates="year", cascade="all, delete-orphan", collection_class=set
    )
    announcements: Mapped[set["Announcement"]] = relationship(
        "Announcement", back_populates="year", cascade="all, delete-orphan", collection_class=set
    )
    weeks: Mapped[set["Week"]] = relationship(
        "Week", back_populates="year", cascade="all, delete-orphan", collection_class=set
    )
    events: Mapped[set["Event"]] = relationship(
        "Event", back_populates="year", cascade="all, delete-orphan", collection_class=set
    )

    # Indexes
    __table_args__ = (Index("idx_year", "year", unique=True),)
