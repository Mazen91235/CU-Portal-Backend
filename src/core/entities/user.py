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
    AssociationProxy,
    association_proxy,
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
    from .userNotification import UserNotification
    from .log import Log
    from .subject import Subject
    from .userSubjectLink import UserSubjectLink
    from .requestLimit import RequestLimit
    from .event import Event
    from .userEvent import UserEvent
    from .note import Note
    from .attachment import Attachment
    from .device import Device
    from .token import Token


class User(Base):
    # Tablename
    __tablename__ = "users"

    # Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(13), nullable=False)
    gender: Mapped[str] = mapped_column(String(6), nullable=False)
    study_type: Mapped[Optional["User.StudyType"]] = mapped_column(
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
        String(500), nullable=True
    )
    ips: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON), nullable=True, default=list
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
    def google_details_token(self) -> Optional[str]:
        return getattr(self, "_google_details_token", None)

    @google_details_token.setter
    def google_details_token(self, value: Optional[str]) -> None:
        setattr(self, "_google_details_token", value)

    @property
    def refresh_token(self) -> Optional[str]:
        return getattr(self, "_refresh_token", None)

    @refresh_token.setter
    def refresh_token(self, value: Optional[str]) -> None:
        setattr(self, "_refresh_token", value)

    # Relationships
    avatar_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("attachments.id", ondelete="SET NULL", name="fk_attachment_user"),
        nullable=True,
    )
    avatar: Mapped[Optional["Attachment"]] = relationship(
        "Attachment",
        back_populates="user",
        foreign_keys=[avatar_id],
    )
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
    materials: Mapped[set["Material"]] = relationship(
        "Material",
        back_populates="author",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    tasks: Mapped[set["Task"]] = relationship(
        "Task",
        back_populates="author",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    announcements: Mapped[set["Announcement"]] = relationship(
        "Announcement",
        back_populates="author",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    notifications: AssociationProxy[set["Notification"]] = association_proxy(
        "user_notifications",
        "notification",
        creator=lambda notification: __import__(
            "core.entities.userNotification", fromlist=["UserNotification"]
        ).UserNotification(notification=notification),
    )
    user_notifications: Mapped[set["UserNotification"]] = relationship(
        "UserNotification",
        back_populates="user",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    events: Mapped[set["Event"]] = relationship(
        "Event",
        back_populates="author",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    going_events: AssociationProxy[set["Event"]] = association_proxy(
        "user_events",
        "event",
        creator=lambda event: __import__(
            "core.entities.userEvent", fromlist=["UserEvent"]
        ).UserEvent(event=event),
    )
    user_events: Mapped[set["UserEvent"]] = relationship(
        "UserEvent",
        back_populates="user",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    notes: Mapped[set["Note"]] = relationship(
        "Note",
        back_populates="author",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    logs: Mapped[set["Log"]] = relationship(
        "Log", back_populates="user", cascade="all, delete-orphan", collection_class=set
    )
    subjects: AssociationProxy[set["Subject"]] = association_proxy(
        "user_subject_links",
        "subject",
        creator=lambda subject: __import__(
            "core.entities.userSubjectLink", fromlist=["UserSubjectLink"]
        ).UserSubjectLink(subject=subject),
    )
    user_subject_links: Mapped[set["UserSubjectLink"]] = relationship(
        "UserSubjectLink",
        back_populates="user",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    request_limits: Mapped[set["RequestLimit"]] = relationship(
        "RequestLimit",
        back_populates="user",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    attachments: Mapped[set["Attachment"]] = relationship(
        "Attachment",
        back_populates="author",
        cascade="all, delete-orphan",
        foreign_keys="Attachment.author_id",
        collection_class=set,
    )
    devices: Mapped[set["Device"]] = relationship(
        "Device",
        back_populates="user",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    tokens: Mapped[set["Token"]] = relationship(
        "Token",
        back_populates="user",
        cascade="all, delete-orphan",
        collection_class=set,
    )

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Arguments
    __table_args__ = (
        Index("idx_user_email", "email", unique=True),
        Index("idx_user_phone", "phone", unique=True),
        Index("idx_user_google_id", "google_id", unique=True),
    )
    __mapper_args__ = {
        "version_id_col": version,
    }

    # Validation
    @validates("study_type")
    def validate_study_type(self, key, value) -> int:
        if value not in self.StudyType.__dict__.values():
            raise ValueError("Invalid study type")
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

    class StudyType(str, Enum):
        MAINSTREAM = "Mainstream"
        CREDIT = "Credit"

    MAX_ALLOWED_FILE_SIZE_MB = 10  # 10 MB in bytes
    MAX_ALLOWED_FILE_SIZE_B = MAX_ALLOWED_FILE_SIZE_MB * 1024**2  # 10 MB in bytes
