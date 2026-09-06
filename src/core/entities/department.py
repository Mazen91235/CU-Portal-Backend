from __future__ import annotations
from enum import Enum
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
    from .faculty import Faculty
    from .subject import Subject
    from .task import Task
    from .announcement import Announcement
    from .event import Event
    from .week import Week


class Department(Base):
    # Tablename
    __tablename__ = "departments"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    code: Mapped[str] = mapped_column(
        String(10), nullable=True
    )  # e.g., "CMP", "CSE", "ECE"
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )
    study_type: Mapped["Department.StudyType"] = mapped_column(
        String(12), nullable=True
    )  # Mainstream, Credit, etc.

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
    faculty_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("faculties.id", ondelete="cascade", name="fk_faculty_department"),
        nullable=False,
    )
    faculty: Mapped["Faculty"] = relationship(
        "Faculty", back_populates="departments", cascade="save-update, merge"
    )
    users: Mapped[set["User"]] = relationship(
        "User", back_populates="department", cascade="all, delete-orphan", collection_class=set
    )
    subjects: Mapped[set["Subject"]] = relationship(
        "Subject", back_populates="department", cascade="all, delete-orphan", collection_class=set
    )
    announcements: Mapped[set["Announcement"]] = relationship(
        "Announcement", back_populates="department", cascade="all, delete-orphan", collection_class=set
    )
    weeks: Mapped[set["Week"]] = relationship(
        "Week", back_populates="department", cascade="all, delete-orphan", collection_class=set
    )
    events: Mapped[set["Event"]] = relationship(
        "Event", back_populates="department", cascade="all, delete-orphan", collection_class=set
    )

    # Indexes
    __table_args__ = (
        # Composite Indexes
        Index("idx_department_faculty_name", "faculty_id", "name"),
        Index("idx_department_study_type_name", "study_type", "name"),
        Index(
            "idx_department_faculty_study_type_name",
            "faculty_id",
            "study_type",
            "name",
            unique=True,
        ),
        Index(
            "idx_department_faculty_study_type_code",
            "faculty_id",
            "study_type",
            "code",
            unique=True,
        ),
    )

    # Attributes
    class StudyType(str, Enum):
        MAINSTREAM = "Mainstream"
        CREDIT = "Credit"
        BOTH = "Both"
