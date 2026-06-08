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
    TYPE_CHECKING,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from .user import User
    from .year import Year
    from .department import Department
    from .faculty import Faculty
    from .task import Task
    from .announcement import Announcement
    from .material import Material
    from .grade import Grade
    from .mark import Mark
    from .question import Question
    from .roadmapCourse import RoadmapCourse


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
    grades: Mapped[list["Grade"]] = relationship(
        "Grade", back_populates="subject", cascade="all, delete-orphan"
    )
    marks: Mapped[list["Mark"]] = relationship(
        "Mark", back_populates="subject", cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="subject", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(
        "User", secondary="user_subject_links", back_populates="subjects"
    )
    roadmap_courses: Mapped[list["RoadmapCourse"]] = relationship(
        "RoadmapCourse", back_populates="subject", cascade="all, delete-orphan"
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

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "details": self.details,
            "is_old": self.is_old,
            "year_rank": self.year_rank,
            "term": self.term,
            "credits": self.credits,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "year": self.year.to_dict() if self.year else None,
            "department": self.department.to_dict() if self.department else None,
            "faculty": self.faculty.to_dict() if self.faculty else None,
            "users_count": len(self.users) if self.users else 0,
            "users": [user.to_dict() for user in self.users] if self.users else [],
            "tasks": [task.to_dict() for task in self.tasks] if self.tasks else [],
            "announcements": (
                [announcement.to_dict() for announcement in self.announcements]
                if self.announcements
                else []
            ),
            "materials": (
                [material.to_dict() for material in self.materials]
                if self.materials
                else []
            ),
            "grades": [grade.to_dict() for grade in self.grades] if self.grades else [],
            "marks": [mark.to_dict() for mark in self.marks] if self.marks else [],
            "questions": (
                [question.to_dict() for question in self.questions]
                if self.questions
                else []
            ),
            "roadmap_courses": (
                [roadmap_course.to_dict() for roadmap_course in self.roadmap_courses]
                if self.roadmap_courses
                else []
            ),
        }

    class Model(TypedDict):
        id: int
        name: str
        code: Optional[str]
        details: dict
        is_old: bool
        year_rank: Optional[int]
        term: Optional[int]
        credits: Optional[int]
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        year: Optional[Year.Model]
        department: Optional[Department.Model]
        faculty: Optional[Faculty.Model]
        users_count: int
        users: list["User.Model"]
        tasks: list["Task.Model"]
        announcements: list["Announcement.Model"]
        materials: list["Material.Model"]
        grades: list["Grade.Model"]
        marks: list["Mark.Model"]
        questions: list["Question.Model"]
        roadmap_courses: list["RoadmapCourse.Model"]
