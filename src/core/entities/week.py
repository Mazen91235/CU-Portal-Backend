from __future__ import annotations

from .base import (
    Base,
    Integer,
    TIMESTAMP,
    datetime,
    ForeignKey,
    Index,
    Mapped,
    Optional,
    TimezoneHandler,
    TYPE_CHECKING,
    mapped_column,
    relationship,
    AssociationProxy,
    association_proxy,
    func,
    text,
    ExcludeConstraint,
)

if TYPE_CHECKING:
    from .faculty import Faculty
    from .department import Department
    from .year import Year
    from .material import Material
    from .weekItem import WeekItem


class Week(Base):
    # Tablename
    __tablename__ = "weeks"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
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

    # Relationships
    materials: AssociationProxy[set["Material"]] = association_proxy(
        "week_items",
        "material",
        creator=lambda material: __import__(
            "core.entities.weekItem", fromlist=["WeekItem"]
        ).WeekItem(material=material),
    )
    week_items: Mapped[set["WeekItem"]] = relationship(
        "WeekItem",
        back_populates="week",
        cascade="all, delete-orphan",
        collection_class=set,
    )

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Arguments
    __table_args__ = (
        ExcludeConstraint(
            (
                func.daterange(
                    start_date, start_date + text("INTERVAL '7 days'"), "[)"
                ),
                "&&",
            ),
            name="exclude_overlapping_weeks_within_7_days",
            using="gist",
        ),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }
