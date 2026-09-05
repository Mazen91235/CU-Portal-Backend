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
    from .faculty import Faculty
    from .department import Department
    from .year import Year
    from .material import Material


class Week(Base):
    # Tablename
    __tablename__ = "weeks"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    end_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

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
    faculty_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("faculties.id", ondelete="CASCADE", name="fk_faculty_week"),
        nullable=False,
    )
    faculty: Mapped["Faculty"] = relationship("Faculty", back_populates="weeks")
    department_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE", name="fk_department_week"),
        nullable=False,
    )
    department: Mapped["Department"] = relationship(
        "Department", back_populates="weeks"
    )
    year_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("years.id", ondelete="CASCADE", name="fk_year_week"),
        nullable=False,
    )
    year: Mapped["Year"] = relationship("Year", back_populates="weeks")
    materials: Mapped[set["Material"]] = relationship(
        "Material", back_populates="week", cascade="all, delete-orphan", collection_class=set
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_week_faculty_id_department_id_year_id_week_number",
            "faculty_id",
            "department_id",
            "year_id",
            "week_number",
            unique=True,
        ),
    )
