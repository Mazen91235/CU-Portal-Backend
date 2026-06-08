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
    from .user import User
    from .exactRole import ExactRole


class Role(Base):
    # Tablename
    __tablename__ = "roles"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=True, default=4)

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
    users: Mapped[list["User"]] = relationship("User", back_populates="role")
    exact_roles: Mapped[list["ExactRole"]] = relationship(
        "ExactRole", secondary="role_links", back_populates="roles"
    )

    # Indexes
    __table_args__ = (Index("idx_role_name", "name", unique=True),)

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "permissions": (
                [exact_role.name for exact_role in self.exact_roles]
                if self.exact_roles
                else []
            ),
            "permissions_count": len(self.exact_roles) if self.exact_roles else 0,
            "users_count": len(self.users) if self.users else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "users": [user.to_dict() for user in self.users] if self.users else [],
        }

    class Model(TypedDict):
        id: int
        name: str
        level: Optional[int]
        permissions: list[str]
        permissions_count: int
        users_count: int
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        users: list["User.Model"]
