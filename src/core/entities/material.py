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
    from .subject import Subject
    from .week import Week
    from .attachment import Attachment


class Material(Base):
    # Tablename
    __tablename__ = "materials"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    material_type: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )

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

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Relationships
    subject_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE", name="fk_subject_material"),
        nullable=True,
    )
    subject: Mapped[Optional["Subject"]] = relationship(
        "Subject", back_populates="materials", cascade="save-update, merge"
    )
    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_user_material"),
        nullable=False,
    )
    author: Mapped["User"] = relationship("User", back_populates="materials")
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE", name="fk_parent_material"),
        nullable=True,
    )
    parent: Mapped[Optional["Material"]] = relationship(
        "Material", remote_side="Material.id", back_populates="children"
    )
    children: Mapped[set["Material"]] = relationship(
        "Material",
        back_populates="parent",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    week_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("weeks.id", ondelete="SET NULL", name="fk_week_material"),
        nullable=True,
    )
    week: Mapped[Optional["Week"]] = relationship(
        "Week", back_populates="materials", cascade="save-update, merge"
    )
    attachment: Mapped[Optional["Attachment"]] = relationship(
        "Attachment",
        back_populates="material",
        cascade="save-update, merge",
        uselist=False,
    )

    # Arguments
    __table_args__ = (
        Index(
            "idx_material_name_subject_id_parent_id",
            "name",
            "subject_id",
            "parent_id",
            unique=True,
        ),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }
