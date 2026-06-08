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

    # Indexes
    __table_args__ = (
        # Composite Indexes
        Index("idx_request_limit_ip_created_at", "ip", "created_at"),
    )

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "ip": self.ip,
            "route": self.route,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.to_dict() if self.user else None,
        }

    class Model(TypedDict):
        id: int
        ip: Optional[str]
        route: Optional[str]
        status: Optional[bool]
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        user: Optional[User.Model]
