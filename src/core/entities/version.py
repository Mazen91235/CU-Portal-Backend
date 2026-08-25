from __future__ import annotations

from .base import (
    Base,
    Integer,
    String,
    TIMESTAMP,
    datetime,
    JSON,
    MutableDict,
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
    from .release import Release


class Version(Base):
    # Tablename
    __tablename__ = "versions"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

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
    releases: Mapped[set["Release"]] = relationship(
        "Release", back_populates="version", cascade="all, delete-orphan", collection_class=set
    )

    # Indexes
    __table_args__ = (
        Index("idx_version_version_number", "version_number", unique=True),
    )
