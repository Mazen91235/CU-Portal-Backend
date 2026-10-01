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
    TypedDict,
    AssociationProxy,
    association_proxy,
    TYPE_CHECKING,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from .week import Week
    from .material import Material
    from .user import User
    from .userCompletion import UserCompletion


class WeekItem(Base):
    # Tablename
    __tablename__ = "week_items"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")

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
    week_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("weeks.id", ondelete="CASCADE", name="fk_week_week_item"),
        nullable=False,
    )
    week: Mapped["Week"] = relationship("Week", back_populates="week_items")
    material_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE", name="fk_material_week_item"),
        nullable=False,
    )
    material: Mapped["Material"] = relationship(
        "Material", back_populates="week_items"
    )
    completed_by_users: AssociationProxy[set["User"]] = association_proxy(
        "user_completions",
        "user",
        creator=lambda user: __import__(
            "core.entities.userCompletion", fromlist=["UserCompletion"]
        ).UserCompletion(user=user),
    )
    user_completions: Mapped[set["UserCompletion"]] = relationship(
        "UserCompletion",
        back_populates="week_item",
        cascade="all, delete-orphan",
        collection_class=set,
    )

    # Versioning
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )

    # Arguments
    __table_args__ = (
        Index(
            "idx_week_item_week_id_material_id",
            "week_id",
            "material_id",
            unique=True,
        ),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }
