from __future__ import annotations

from .base import (
    Base,
    Integer,
    TIMESTAMP,
    datetime,
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
    from .weekItem import WeekItem
    from .task import Task


class UserCompletion(Base):
    # Tablename
    __tablename__ = "user_completions"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

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
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_user_completion"),
        nullable=False,
    )
    user: Mapped["User"] = relationship("User", back_populates="user_completions")
    week_item_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "week_items.id",
            ondelete="CASCADE",
            name="fk_week_item_user_completion",
        ),
        nullable=True,
    )
    week_item: Mapped[Optional["WeekItem"]] = relationship(
        "WeekItem", back_populates="user_completions"
    )
    task_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE", name="fk_task_user_completion"),
        nullable=True,
    )
    task: Mapped[Optional["Task"]] = relationship(
        "Task", back_populates="user_completions"
    )

    # Versioning
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )

    # Arguments
    __table_args__ = (
        Index(
            "idx_user_completion_user_id_week_item_id",
            "user_id",
            "week_item_id",
            unique=True,
        ),
        Index(
            "idx_user_completion_user_id_task_id",
            "user_id",
            "task_id",
            unique=True,
        ),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }
