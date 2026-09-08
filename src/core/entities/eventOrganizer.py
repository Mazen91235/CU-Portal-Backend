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
    from .event import Event
    from .attachment import Attachment


class EventOrganizer(Base):
    # Tablename
    __tablename__ = "event_organizers"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )  # eg. (url, urls, links)

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
    events: Mapped[set["Event"]] = relationship(
        "Event",
        back_populates="event_organizer",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    logo_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "attachments.id", ondelete="SET NULL", name="fk_attachment_event_organizer"
        ),
        nullable=False,
    )
    logo: Mapped[Optional["Attachment"]] = relationship(
        "Attachment", back_populates="event_organizer_logo", foreign_keys=[logo_id]
    )
    attachments: Mapped[set["Attachment"]] = relationship(
        "Attachment",
        back_populates="event_organizer",
        cascade="save-update, merge",
        foreign_keys="Attachment.event_organizer_id",
        collection_class=set,
    )

    # Arguments
    __table_args__ = (Index("idx_event_organizer_name", "name", unique=True),)
    __mapper_args__ = {
        "version_id_col": version,
    }
