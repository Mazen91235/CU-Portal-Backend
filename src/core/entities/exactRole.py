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
    TYPE_CHECKING,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from .role import Role


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
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="role_links", back_populates="exact_roles"
    )

    # Indexes
    __table_args__ = (Index("idx_exact_role_name", "name", unique=True),)

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "roles": [role.to_dict() for role in self.roles] if self.roles else [],
        }

    class Model(TypedDict):
        id: int
        name: str
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        roles: list["Role.Model"]
