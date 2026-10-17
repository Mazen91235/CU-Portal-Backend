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
    from .attachment import Attachment


class Announcement(Base):
    # Tablename
    __tablename__ = "announcements"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(String(3000), nullable=True)
    date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )  # includes urls, links, and other additional details

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
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
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
    attachments: Mapped[set["Attachment"]] = relationship(
        "Attachment",
        back_populates="announcement",
        cascade="save-update, merge",
        collection_class=set,
    )

    # Arguments
    __table_args__ = (
        Index(
            "idx_announcement_title_subject_id_date",
            "title",
            "subject_id",
            "date",
            unique=True,
        ),
        Index("idx_announcement_subject_id_date", "subject_id", "date"),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }
