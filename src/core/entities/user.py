from __future__ import annotations
from enum import Enum
from .base import (
    Base,
    Integer,
    String,
    Boolean,
    TIMESTAMP,
    datetime,
    JSON,
    MutableDict,
    MutableList,
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

if TYPE_CHECKING:
    from .year import Year
    from .department import Department
    from .faculty import Faculty
    from .role import Role
    from .pendingUser import PendingUser
    from .material import Material
    from .task import Task
    from .announcement import Announcement
    from .notification import Notification
    from .log import Log
    from .subject import Subject
    from .requestLimit import RequestLimit
    from .event import Event
    from .note import Note


class User(Base):
    # Tablename
    __tablename__ = "users"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(13), nullable=False)
    gender: Mapped[str] = mapped_column(String(6), nullable=False)
    type: Mapped[Optional["User.Type"]] = mapped_column(
        String(12), nullable=True
    )  # Mainstream, Credit
    section: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    is_early_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    manages: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )
    details: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default=dict
    )
    google_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    google_name: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    google_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    google_avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_refresh_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    ips: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON), nullable=True, default=list
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refresh_expire_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
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

    # Not Mapped
    @property
    def url(self) -> Optional[str]:
        return getattr(self, "_url", None)

    @url.setter
    def url(self, value: Optional[str]) -> None:
        setattr(self, "_url", value)

    @property
    def google_details_token(self) -> Optional[str]:
        return getattr(self, "_google_details_token", None)

    @google_details_token.setter
    def google_details_token(self, value: Optional[str]) -> None:
        setattr(self, "_google_details_token", value)

    # Relationships
    year_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("years.id", ondelete="CASCADE", name="fk_year_user"),
        nullable=True,
    )
    year: Mapped[Optional["Year"]] = relationship(
        "Year", back_populates="users", cascade="save-update, merge"
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE", name="fk_department_user"),
        nullable=True,
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="users", cascade="save-update, merge"
    )
    faculty_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("faculties.id", ondelete="CASCADE", name="fk_faculty_user"),
        nullable=True,
    )
    faculty: Mapped[Optional["Faculty"]] = relationship(
        "Faculty", back_populates="users", cascade="save-update, merge"
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE", name="fk_role_user"),
        nullable=True,
    )
    role: Mapped[Optional["Role"]] = relationship(
        "Role", back_populates="users", cascade="save-update, merge"
    )
    pending_user: Mapped[Optional["PendingUser"]] = relationship(
        "PendingUser",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    materials: Mapped[list["Material"]] = relationship(
        "Material", back_populates="author", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="author", cascade="all, delete-orphan"
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        "Announcement", back_populates="author", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        secondary="user_notifications",
        back_populates="users",
        cascade="all, delete",
    )
    events: Mapped[list["Event"]] = relationship(
        "Event", back_populates="author", cascade="all, delete-orphan"
    )
    going_events: Mapped[list["Event"]] = relationship(
        "Event",
        secondary="user_events",
        back_populates="attendees",
        cascade="all, delete",
    )
    notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="author", cascade="all, delete-orphan"
    )
    # marks: Mapped[list["Mark"]] = relationship(
    #     "Mark", back_populates="author", cascade="all, delete-orphan"
    # )
    # roadmaps: Mapped[list["Roadmap"]] = relationship(
    #     "Roadmap", back_populates="author", cascade="all, delete-orphan"
    # )
    # questions: Mapped[list["Question"]] = relationship(
    #     "Question", back_populates="author", cascade="all, delete-orphan"
    # )
    # answers: Mapped[list["Answer"]] = relationship(
    #     "Answer", back_populates="author", cascade="all, delete-orphan"
    # )
    # timetables: Mapped[list["Timetable"]] = relationship(
    #     "Timetable", back_populates="author", cascade="all, delete-orphan"
    # )
    # reviews: Mapped[list["Review"]] = relationship(
    #     "Review", back_populates="author", cascade="all, delete-orphan"
    # )
    logs: Mapped[list["Log"]] = relationship(
        "Log", back_populates="user", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["Subject"]] = relationship(
        "Subject",
        secondary="user_subject_links",
        back_populates="users",
        cascade="all, delete",
    )
    request_limits: Mapped[list["RequestLimit"]] = relationship(
        "RequestLimit", back_populates="user", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_email", "email", unique=True),
        Index("idx_user_phone", "phone", unique=True),
        Index("idx_user_google_id", "google_id", unique=True),
        Index("idx_user_google_email", "google_email", unique=True),
        # Composite Indexes
        Index("idx_user_faculty_name", "faculty_id", "name"),
        Index("idx_faculty_department_name", "faculty_id", "department_id", "name"),
        Index("idx_status_faculty_name", "status", "faculty_id", "name"),
        Index(
            "idx_user_refresh_token_refresh_expire_at",
            "refresh_token",
            "refresh_expire_at",
        ),
    )

    # Validation
    @validates("type")
    def validate_type(self, key, value) -> int:
        if value not in self.Type.__dict__.values():
            raise ValueError("Invalid user type")
        return value

    # Attributes
    class RefreshToken:
        EXPIRE_DAYS = 30
        MINIMUM_DAYS = 7

    class GoogleToken:
        TOKEN_LENGTH = 40
        EXPIRE_HOURS = 1

    class VerificationToken:
        EXPIRE_HOURS = 1

    class Type(str, Enum):
        MAINSTREAM = "Mainstream"
        CREDIT = "Credit"

    MAX_ALLOWED_FILE_SIZE_MB = 10  # 10 MB in bytes
    MAX_ALLOWED_FILE_SIZE_B = MAX_ALLOWED_FILE_SIZE_MB * 1024**2  # 10 MB in bytes
