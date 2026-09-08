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
    TYPE_CHECKING,
    mapped_column,
    relationship,
    func,
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

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

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
        "User",
        back_populates="department",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    subjects: Mapped[set["Subject"]] = relationship(
        "Subject",
        back_populates="department",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    announcements: Mapped[set["Announcement"]] = relationship(
        "Announcement",
        back_populates="department",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    weeks: Mapped[set["Week"]] = relationship(
        "Week",
        back_populates="department",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    events: Mapped[set["Event"]] = relationship(
        "Event",
        back_populates="department",
        cascade="all, delete-orphan",
        collection_class=set,
    )

    # Arguments
    __table_args__ = (
        Index(
            "idx_department_faculty_id_study_type_name",
            "faculty_id",
            "study_type",
            func.lower(name),
            unique=True,
        ),
        Index(
            "idx_department_faculty_id_study_type_code",
            "faculty_id",
            "study_type",
            func.lower(code),
            unique=True,
        ),
        Index(
            "idx_department_faculty_id_name",
            "faculty_id",
            func.lower(name),
            unique=True,
        ),
        Index(
            "idx_department_faculty_id_code",
            "faculty_id",
            func.lower(code),
            unique=True,
        ),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }

    # Attributes
    class StudyType(str, Enum):
        MAINSTREAM = "Mainstream"
        CREDIT = "Credit"
        BOTH = "Both"
