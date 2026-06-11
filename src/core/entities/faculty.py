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
    from .department import Department
    from .announcement import Announcement

    # from .event import Event
    # from .roadmap import Roadmap
    # from .question import Question
    # from .timetable import Timetable
    from .task import Task
    from .subject import Subject


class Faculty(Base):
    # Tablename
    __tablename__ = "faculties"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
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
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="faculty", cascade="all, delete-orphan"
    )
    departments: Mapped[list["Department"]] = relationship(
        "Department", back_populates="faculty", cascade="all, delete-orphan"
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        "Announcement", back_populates="faculty", cascade="all, delete-orphan"
    )
    # events: Mapped[list["Event"]] = relationship(
    #     "Event", back_populates="faculty", cascade="all, delete-orphan"
    # )
    # roadmaps: Mapped[list["Roadmap"]] = relationship(
    #     "Roadmap", back_populates="faculty", cascade="all, delete-orphan"
    # )
    # questions: Mapped[list["Question"]] = relationship(
    #     "Question", back_populates="faculty", cascade="all, delete-orphan"
    # )
    # timetables: Mapped[list["Timetable"]] = relationship(
    #     "Timetable", back_populates="faculty", cascade="all, delete-orphan"
    # )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="faculty", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["Subject"]] = relationship(
        "Subject", back_populates="faculty", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("idx_faculty_name", "name", unique=True),)
