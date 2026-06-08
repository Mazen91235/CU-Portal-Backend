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
    role: Mapped["Role"] = relationship("Role", backref="role_links_associations")
    exact_role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "exact_roles.id", ondelete="CASCADE", name="fk_exact_role_role_link"
        ),
        nullable=False,
    )
    exact_role: Mapped["ExactRole"] = relationship(
        "ExactRole", backref="role_links_associations"
    )

    # Indexes
    __table_args__ = (
        # Composite Indexes
        Index("idx_role_exact_role", "role_id", "exact_role_id", unique=True),
        Index("idx_exact_role_role", "exact_role_id", "role_id"),
    )

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "role_id": self.role_id,
            "exact_role_id": self.exact_role_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "role": self.role.to_dict() if self.role else None,
            "exact_role": self.exact_role.to_dict() if self.exact_role else None,
        }

    class Model(TypedDict):
        id: int
        role_id: int
        exact_role_id: int
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        role: Role.Model
        exact_role: ExactRole.Model
