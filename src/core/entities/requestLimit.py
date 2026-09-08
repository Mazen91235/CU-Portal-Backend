from __future__ import annotations

from .base import (
    Base,
    Integer,
    String,
    Boolean,
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


class RequestLimit(Base):
    # Tablename
    __tablename__ = "request_limits"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 support
    route: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # API endpoint or route
    status: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False, nullable=True
    )  # True if the request is passed

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
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", name="fk_user_request_limit", ondelete="SET NULL"),
        nullable=True,
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="request_limits"
    )

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Arguments
    __table_args__ = (
        # Composite Indexes
        Index("idx_request_limit_ip_created_at", "ip", "created_at"),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }
