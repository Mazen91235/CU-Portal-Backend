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
    from .version import Version
    from .releaseItem import ReleaseItem


class Release(Base):
    # Tablename
    __tablename__ = "releases"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    release_number: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

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
    version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("versions.id"), nullable=False
    )
    version: Mapped["Version"] = relationship(
        "Version", back_populates="releases", cascade="all, delete-orphan"
    )
    release_items: Mapped[list["ReleaseItem"]] = relationship(
        "ReleaseItem", back_populates="release", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_release_release_number", "release_number", unique=True),
    )
