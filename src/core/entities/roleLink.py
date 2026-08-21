from __future__ import annotations

from .base import (
    Base,
    Integer,
    ForeignKey,
    Index,
    Mapped,
    TIMESTAMP,
    datetime,
    Optional,
    TimezoneHandler,
    TypedDict,
    TYPE_CHECKING,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from .role import Role
    from .exactRole import ExactRole


class RoleLink(Base):
    # Tablename
    __tablename__ = "role_links"

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
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE", name="fk_role_role_link"),
        nullable=False,
    )
    role: Mapped["Role"] = relationship("Role", back_populates="role_links")
    exact_role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "exact_roles.id", ondelete="CASCADE", name="fk_exact_role_role_link"
        ),
        nullable=False,
    )
    exact_role: Mapped["ExactRole"] = relationship(
        "ExactRole", back_populates="role_links"
    )

    # Indexes
    __table_args__ = (
        # Composite Indexes
        Index("idx_role_exact_role", "role_id", "exact_role_id", unique=True),
        Index("idx_exact_role_role", "exact_role_id", "role_id"),
    )
