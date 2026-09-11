from __future__ import annotations
from enum import Enum
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


class ReleaseItem(Base):
    # Tablename
    __tablename__ = "release_items"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_type: Mapped["ReleaseItem.ItemType"] = mapped_column(
        String(15), nullable=False
    )
    content: Mapped[str] = mapped_column(String(255), nullable=False)

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
    release_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("releases.id"), nullable=False
    )
    release: Mapped["Release"] = relationship("Release", back_populates="release_items")

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Arguments
    __table_args__ = (Index("idx_release_item_release_id", "release_id", unique=False),)
    __mapper_args__ = {
        "version_id_col": version,
    }

    # Attributes
    class ItemType(str, Enum):
        FEATURE = "Feature"
        IMPROVEMENT = "Improvement"
        REFACTORING = "Refactoring"
        SECURITY_FIX = "Security Fix"
        BUG_FIX = "Bug Fix"
