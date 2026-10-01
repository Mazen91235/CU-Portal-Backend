from __future__ import annotations

from .base import (
    Base,
    Integer,
    String,
    TIMESTAMP,
    datetime,
    JSON,
    MutableDict,
    Index,
    Mapped,
    Optional,
    TimezoneHandler,
    TYPE_CHECKING,
    mapped_column,
    relationship,
    func
)

if TYPE_CHECKING:
    from .user import User
    from .department import Department
    from .announcement import Announcement
    from .subject import Subject
    from .event import Event


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

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Relationships
    users: Mapped[set["User"]] = relationship(
        "User", back_populates="faculty", cascade="all, delete-orphan", collection_class=set
    )
    departments: Mapped[set["Department"]] = relationship(
        "Department", back_populates="faculty", cascade="all, delete-orphan", collection_class=set
    )
    announcements: Mapped[set["Announcement"]] = relationship(
        "Announcement", back_populates="faculty", cascade="all, delete-orphan", collection_class=set
    )
    subjects: Mapped[set["Subject"]] = relationship(
        "Subject", back_populates="faculty", cascade="all, delete-orphan", collection_class=set
    )
    events: Mapped[set["Event"]] = relationship(
        "Event", back_populates="faculty", cascade="all, delete-orphan", collection_class=set
    )

    # Arguments
    __table_args__ = (Index("idx_faculty_name", func.lower(name), unique=True),)
    __mapper_args__ = {
        "version_id_col": version,
    }
