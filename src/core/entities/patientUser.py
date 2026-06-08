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
    TYPE_CHECKING,
    mapped_column,
    relationship,
    validates,
)
from pgvector.sqlalchemy import Vector

if TYPE_CHECKING:
    from .patient import Patient


class PatientUser(Base):
    # Tablename
    __tablename__ = "patient_users"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True, name="id")
    name: Mapped[str] = mapped_column(String(50), nullable=False, name="name")
    relation: Mapped[int] = mapped_column(Integer, nullable=False, name="relation")
    voice: Mapped[str] = mapped_column(String(255), nullable=False, name="voice")
    img: Mapped[str] = mapped_column(String(255), nullable=False, name="img")
    img_vector: Mapped[Vector] = mapped_column(
        Vector(128), nullable=False, name="img_vector"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: TimezoneHandler.now("UTC"),
        nullable=False,
        name="created_at",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: TimezoneHandler.now("UTC"),
        onupdate=lambda: TimezoneHandler.now("UTC"),
        nullable=False,
        name="updated_at",
    )

    # Relationships
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        name="patient_id",
    )
    patient: Mapped["Patient"] = relationship("Patient", back_populates="patient_users")

    # Indexes
    __table_args__ = (
        Index(
            "img_vector_idx",
            "img_vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"img_vector": "vector_cosine_ops"},
        ),
    )

    # Validation
    @validates("relation")
    def validate_relation(self, key, value) -> int:
        if value not in self.relationships:
            raise ValueError("Invalid relationship")
        return value

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "relation": self.relation,
            "voice": self.voice,
            "img": self.img,
            "patient_id": self.patient_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "patient": self.patient.to_dict() if self.patient else None,
        }

    class Model(TypedDict):
        id: int
        name: str
        relation: int
        voice: str
        img: str
        img_vector: Vector
        created_at: datetime
        updated_at: datetime
        patient: Optional[Patient.Model]

    # Attributes
    relationships = {
        0: "Parent",
        1: "Sibling",
        2: "Wife/Husband",
        3: "Child",
        4: "Friend",
        5: "Other",
    }

    class Relation:
        PARENT = 0
        SIBLING = 1
        SPOUSE = 2
        CHILD = 3
        FRIEND = 4
        OTHER = 5

    # Methods
    def get_relationship(self):
        return self.relationships.get(self.relation, "Unknown")
