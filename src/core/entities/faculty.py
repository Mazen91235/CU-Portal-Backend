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
    from .event import Event
    from .roadmap import Roadmap
    from .question import Question
    from .timetable import Timetable
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
    events: Mapped[list["Event"]] = relationship(
        "Event", back_populates="faculty", cascade="all, delete-orphan"
    )
    roadmaps: Mapped[list["Roadmap"]] = relationship(
        "Roadmap", back_populates="faculty", cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="faculty", cascade="all, delete-orphan"
    )
    timetables: Mapped[list["Timetable"]] = relationship(
        "Timetable", back_populates="faculty", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="faculty", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["Subject"]] = relationship(
        "Subject", back_populates="faculty", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("idx_faculty_name", "name", unique=True),)

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "users": [user.to_dict() for user in self.users] if self.users else [],
            "departments": (
                [department.to_dict() for department in self.departments]
                if self.departments
                else []
            ),
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
            "tasks": [task.to_dict() for task in self.tasks] if self.tasks else [],
            "subjects": (
                [subject.to_dict() for subject in self.subjects]
                if self.subjects
                else []
            ),
        }

    class Model(TypedDict):
        id: int
        name: str
        details: dict
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        users: list["User.Model"]
        departments: list["Department.Model"]
        announcements: list["Announcement.Model"]
        events: list["Event.Model"]
        roadmaps: list["Roadmap.Model"]
        questions: list["Question.Model"]
        timetables: list["Timetable.Model"]
        tasks: list["Task.Model"]
        subjects: list["Subject.Model"]
