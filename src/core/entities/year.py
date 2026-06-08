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
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="year", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["Subject"]] = relationship(
        "Subject", back_populates="year", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="year", cascade="all, delete-orphan"
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        "Announcement", back_populates="year", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(
        "Event", back_populates="year", cascade="all, delete-orphan"
    )
    roadmaps: Mapped[list["Roadmap"]] = relationship(
        "Roadmap", back_populates="year", cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="year", cascade="all, delete-orphan"
    )
    timetables: Mapped[list["Timetable"]] = relationship(
        "Timetable", back_populates="year", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("idx_year", "year", unique=True),)

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "year": self.year,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "users": [user.to_dict() for user in self.users] if self.users else [],
            "subjects": (
                [subject.to_dict() for subject in self.subjects]
                if self.subjects
                else []
            ),
            "tasks": [task.to_dict() for task in self.tasks] if self.tasks else [],
            "announcements": (
                [announcement.to_dict() for announcement in self.announcements]
                if self.announcements
                else []
            ),
            "events": [event.to_dict() for event in self.events] if self.events else [],
            "roadmaps": (
                [roadmap.to_dict() for roadmap in self.roadmaps]
                if self.roadmaps
                else []
            ),
            "questions": (
                [question.to_dict() for question in self.questions]
                if self.questions
                else []
            ),
            "timetables": (
                [timetable.to_dict() for timetable in self.timetables]
                if self.timetables
                else []
            ),
        }

    class Model(TypedDict):
        id: int
        year: int
        details: dict
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        users: list[User.Model]
        subjects: list[Subject.Model]
        tasks: list[Task.Model]
        announcements: list[Announcement.Model]
        events: list[Event.Model]
        roadmaps: list[Roadmap.Model]
        questions: list[Question.Model]
        timetables: list[Timetable.Model]
