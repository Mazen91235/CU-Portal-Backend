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
)
from sqlalchemy.dialects.postgresql import UUID
from uuid import UUID as UUIDValue

if TYPE_CHECKING:
    from .user import User


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[UUIDValue] = mapped_column(UUID(as_uuid=True), nullable=False)
    device_token: Mapped[str] = mapped_column(String(500), nullable=False)

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
        ForeignKey("users.id", ondelete="CASCADE", name="fk_user_device"),
        nullable=False,
    )
    user: Mapped["User"] = relationship("User", back_populates="devices")

    # Versioning
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )

    # Arguments
    __table_args__ = (
        Index("idx_device_user_id", "user_id"),
        Index("idx_device_device_id", "device_id", unique=True),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }
