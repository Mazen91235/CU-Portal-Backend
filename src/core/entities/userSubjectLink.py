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
    from .subject import Subject


class UserSubjectLink(Base):
    # Tablename
    __tablename__ = "user_subject_links"

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

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Relationships
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_user_subject_link"),
        nullable=False,
    )
    user: Mapped["User"] = relationship("User", back_populates="user_subject_links")
    subject_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "subjects.id", ondelete="CASCADE", name="fk_subject_user_subject_link"
        ),
        nullable=False,
    )
    subject: Mapped["Subject"] = relationship(
        "Subject", back_populates="user_subject_links"
    )

    # Arguments
    __table_args__ = (
        Index(
            "idx_user_subject_link_user_id_subject_id",
            "user_id",
            "subject_id",
            unique=True,
        ),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }
