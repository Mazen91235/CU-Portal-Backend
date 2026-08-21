from __future__ import annotations

from .base import (
    Base,
    Integer,
    String,
    TIMESTAMP,
    datetime,
    Index,
    Mapped,
    Optional,
    TimezoneHandler,
    TypedDict,
    AssociationProxy,
    association_proxy,
    TYPE_CHECKING,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from .role import Role
    from .roleLink import RoleLink


class ExactRole(Base):
    # Tablename
    __tablename__ = "exact_roles"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)

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
    roles: AssociationProxy[list["Role"]] = association_proxy(
        "role_links",
        "role",
        creator=lambda role: __import__(
            "core.entities.roleLink", fromlist=["RoleLink"]
        ).RoleLink(role=role),
    )
    role_links: Mapped[list["RoleLink"]] = relationship(
        "RoleLink", back_populates="exact_role", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("idx_exact_role_name", "name", unique=True),)
