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

    # Relationships
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_user_subject_link"),
        nullable=False,
    )
    user: Mapped["User"] = relationship(
        "User", backref="user_subject_links_associations"
    )
    subject_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "subjects.id", ondelete="CASCADE", name="fk_subject_user_subject_link"
        ),
        nullable=False,
    )
    subject: Mapped["Subject"] = relationship(
        "Subject", backref="user_subject_links_associations"
    )

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subject_id": self.subject_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.to_dict() if self.user else None,
            "subject": self.subject.to_dict() if self.subject else None,
        }

    class Model(TypedDict):
        id: int
        user_id: int
        subject_id: int
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        user: Optional[User.Model]
        subject: Optional[Subject.Model]
