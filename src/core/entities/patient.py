from __future__ import annotations

from .base import (
    Base,
    Integer,
    String,
    TIMESTAMP,
    datetime,
    ForeignKey,
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
    from .patientUser import PatientUser


class Patient(Base):
    # Tablename
    __tablename__ = "patients"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True, name="id")
    name: Mapped[str] = mapped_column(String(50), nullable=False, name="name")
    token: Mapped[str] = mapped_column(
        String(8), unique=True, nullable=False, name="token"
    )  # Used for patient login
    refresh_token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, name="refresh_token"
    )  # Used for patient authentication

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
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        name="user_id",
    )
    user: Mapped["User"] = relationship("User", back_populates="patients")
    patient_users: Mapped[list["PatientUser"]] = relationship(
        "PatientUser", back_populates="patient", cascade="all, delete-orphan"
    )

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "token": self.token,
            "refresh_token": self.refresh_token,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "user": self.user.to_dict() if self.user else None,
            "patient_users": (
                [patient_user.to_dict() for patient_user in self.patient_users]
                if self.patient_users
                else []
            ),
        }

    class Model(TypedDict):
        id: int
        name: str
        token: str
        refresh_token: str
        created_at: datetime
        updated_at: datetime
        user: Optional[User.Model]
        patient_users: list[PatientUser.Model]
