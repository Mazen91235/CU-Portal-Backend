from __future__ import annotations

from .base import (
    Base,
    Integer,
    String,
    Boolean,
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
    AssociationProxy,
    association_proxy,
    TYPE_CHECKING,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from .user import User
    from .userSubjectLink import UserSubjectLink
    from .year import Year
    from .department import Department
    from .faculty import Faculty
    from .task import Task
    from .announcement import Announcement
    from .material import Material

    # from .grade import Grade
    # from .mark import Mark
    # from .question import Question
    # from .roadmapCourse import RoadmapCourse


class Subject(Base):
    # Tablename
    __tablename__ = "subjects"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(
        String(15), nullable=True
    )  # e.g., "CS101", "MATH202"
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )
    is_old: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    year_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    term: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

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
    year_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("years.id", ondelete="CASCADE", name="fk_year_subject"),
        nullable=True,
    )
    year: Mapped[Optional["Year"]] = relationship(
        "Year", back_populates="subjects", cascade="save-update, merge"
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE", name="fk_department_subject"),
        nullable=True,
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="subjects"
    )
    faculty_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("faculties.id", ondelete="CASCADE", name="fk_faculty_subject"),
        nullable=True,
    )
    faculty: Mapped[Optional["Faculty"]] = relationship(
        "Faculty", back_populates="subjects", cascade="save-update, merge"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="subject", cascade="all, delete-orphan"
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        "Announcement", back_populates="subject", cascade="all, delete-orphan"
    )
    materials: Mapped[list["Material"]] = relationship(
        "Material", back_populates="subject", cascade="all, delete-orphan"
    )
    # grades: Mapped[list["Grade"]] = relationship(
    #     "Grade", back_populates="subject", cascade="all, delete-orphan"
    # )
    # marks: Mapped[list["Mark"]] = relationship(
    #     "Mark", back_populates="subject", cascade="all, delete-orphan"
    # )
    # questions: Mapped[list["Question"]] = relationship(
    #     "Question", back_populates="subject", cascade="all, delete-orphan"
    # )
    users: AssociationProxy[list["User"]] = association_proxy(
        "user_subject_links",
        "user",
        creator=lambda user: __import__(
            "core.entities.userSubjectLink", fromlist=["UserSubjectLink"]
        ).UserSubjectLink(user=user),
    )
    user_subject_links: Mapped[list["UserSubjectLink"]] = relationship(
        "UserSubjectLink",
        back_populates="subject",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        # Composite Indexes
        Index(
            "idx_subject_faculty_department_year_code",
            "faculty_id",
            "department_id",
            "year_id",
            "code",
            unique=True,
        ),
        Index(
            "idx_subject_faculty_department_year_name",
            "faculty_id",
            "department_id",
            "year_id",
            "code",
        ),
        Index(
            "idx_subject_year_department_is_old_name",
            "year_id",
            "department_id",
            "is_old",
            "name",
        ),
    )
