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
    TYPE_CHECKING,
    mapped_column,
    relationship,
    func,
)

if TYPE_CHECKING:
    from .user import User


class Note(Base):
    # Tablename
    __tablename__ = "notes"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    date: Mapped[Optional[datetime]] = mapped_column(
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
    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_note"),
        nullable=False,
    )
    author: Mapped["User"] = relationship("User", back_populates="notes")

    # Indexes
    __table_args__ = (
        Index(
            "idx_note_title_author_id_content_date",
            func.lower(title),
            "author_id",
            func.lower(content),
            "date",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )
