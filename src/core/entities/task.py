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


class Task(Base):
    # Tablename
    __tablename__ = "tasks"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    task_type: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )  # e.g., "Exam", "Assignment", "Project", "Task"
    url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )  # includes urls, links, and other additional details
    deadline: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
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
    subject_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE", name="fk_subject_task"),
        nullable=True,
    )
    subject: Mapped[Optional["Subject"]] = relationship(
        "Subject", back_populates="tasks"
    )
    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", name="fk_user_task", ondelete="SET NULL"),
        nullable=False,
    )
    author: Mapped["User"] = relationship("User", back_populates="tasks")
    attachments: Mapped[set["Attachment"]] = relationship(
        "Attachment",
        back_populates="task",
        cascade="save-update, merge",
        collection_class=set,
    )

    # Indexes
    __table_args__ = (
        # Composite Indexes
        Index(
            "idx_task_task_type_subject_id_name",
            "task_type",
            "subject_id",
            "name",
        ),
    )
