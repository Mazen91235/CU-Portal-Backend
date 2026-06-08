from __future__ import annotations

from .base import (
    Base,
    Integer,
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
    TYPE_CHECKING,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from .user import User
    from .year import Year
    from .department import Department
    from .faculty import Faculty
    from .subject import Subject


class Announcement(Base):
    # Tablename
    __tablename__ = "announcements"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    urls: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON), nullable=True, default=list
    )
    links: Mapped[list[str]] = mapped_column(
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
    year_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("years.id", ondelete="CASCADE", name="fk_year_announcement"),
        nullable=True,
    )
    year: Mapped[Optional["Year"]] = relationship(
        "Year", back_populates="announcements", cascade="save-update, merge"
    )
    faculty_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("faculties.id", ondelete="CASCADE", name="fk_faculty_announcement"),
        nullable=True,
    )
    faculty: Mapped[Optional["Faculty"]] = relationship(
        "Faculty", back_populates="announcements", cascade="save-update, merge"
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "departments.id", ondelete="CASCADE", name="fk_department_announcement"
        ),
        nullable=True,
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="announcements"
    )
    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", name="fk_user_announcement", ondelete="SET NULL"),
        nullable=False,
    )
    author: Mapped["User"] = relationship("User", back_populates="announcements")
    subject_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE", name="fk_subject_announcement"),
        nullable=True,
    )
    subject: Mapped[Optional["Subject"]] = relationship(
        "Subject", back_populates="announcements"
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_announcement_faculty_department_year_subject",
            "faculty_id",
            "department_id",
            "year_id",
            "subject_id",
        ),
    )

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "date": self.date.isoformat() if self.date else None,
            "urls": self.urls,
            "links": self.links,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "year": self.year.to_dict() if self.year else None,
            "faculty": self.faculty.to_dict() if self.faculty else None,
            "department": self.department.to_dict() if self.department else None,
            "author": self.author.to_dict() if self.author else None,
            "subject": self.subject.to_dict() if self.subject else None,
        }

    class Model(TypedDict):
        id: int
        title: Optional[str]
        content: Optional[str]
        date: Optional[datetime]
        urls: list[str]
        links: list[str]
        details: dict
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        year: Optional[Year.Model]
        faculty: Optional[Faculty.Model]
        department: Optional[Department.Model]
        author: User.Model
        subject: Optional[Subject.Model]
