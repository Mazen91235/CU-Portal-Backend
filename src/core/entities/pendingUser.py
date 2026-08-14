from __future__ import annotations

from .base import (
    Base,
    Integer,
    String,
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
    from .attachment import Attachment


class PendingUser(Base):
    # Tablename
    __tablename__ = "pending_users"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(100), nullable=False)

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
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_pending_user"),
        nullable=False,
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="pending_user", cascade="save-update, merge"
    )
    attachment: Mapped[Optional["Attachment"]] = relationship(
        "Attachment", back_populates="pending_user", cascade="save-update, merge"
    )

    # Indexes
    __table_args__ = (Index("idx_pending_user_user_id", "user_id", unique=True),)
