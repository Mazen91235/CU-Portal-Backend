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
    from .user import User


class Log(Base):
    # Tablename
    __tablename__ = "logs"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(30), nullable=True)
    entity: Mapped[str] = mapped_column(String(30), nullable=True)
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    response_code: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )
    source: Mapped[str] = mapped_column(String(50), nullable=True)
    route: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # Store the endpoint route or source of the log
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

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
        ForeignKey(
            "users.id", ondelete="SET NULL", onupdate="CASCADE", name="fk_user_log"
        ),
        nullable=True,
    )
    user: Mapped[Optional["User"]] = relationship("User", back_populates="logs")

    # Indexes
    __table_args__ = (
        Index("idx_log_level", "level"),
        # Composite Indexes
        Index("idx_log_created_at_level", "created_at", "level"),
        Index("idx_log_ip_created_at_level", "ip", "created_at", "level"),
        Index(
            "idx_log_created_at_type_action_entity_user_id_message_route",
            "created_at",
            "level",
            "action",
            "entity",
            "user_id",
            "message",
            "route",
        ),
    )
