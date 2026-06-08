from __future__ import annotations

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
    type: Mapped[Optional[str]] = mapped_column(
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
    # grades: Mapped[list["Grade"]] = relationship(
    #     "Grade", back_populates="author", cascade="all, delete-orphan"
    # )
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
    # marks: Mapped[list["Mark"]] = relationship(
    #     "Mark", back_populates="author", cascade="all, delete-orphan"
    # )
    # events: Mapped[list["Event"]] = relationship(
    #     "Event", back_populates="author", cascade="all, delete-orphan"
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
    # going_events: Mapped[list["Event"]] = relationship(
    #     "Event", secondary="event_users", back_populates="users", cascade="all, delete"
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

    # Representation
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "password": self.password,
            "phone": self.phone,
            "gender": self.gender,
            "type": self.type,
            "section": self.section,
            "status": self.status,
            "is_early_access": self.is_early_access,
            "manages": self.manages,
            "details": self.details,
            "google_id": self.google_id,
            "google_name": self.google_name,
            "google_email": self.google_email,
            "google_avatar": self.google_avatar,
            "google_refresh_token": self.google_refresh_token,
            "ips": self.ips,
            "refresh_token": self.refresh_token,
            "refresh_expire_at": (
                self.refresh_expire_at.isoformat() if self.refresh_expire_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "year": self.year.to_dict() if self.year else None,
            "department": self.department.to_dict() if self.department else None,
            "faculty": self.faculty.to_dict() if self.faculty else None,
            "role": self.role.to_dict() if self.role else None,
            "pending_user": self.pending_user.to_dict() if self.pending_user else None,
            "materials": (
                [material.to_dict() for material in self.materials]
                if self.materials
                else []
            ),
            "grades": [grade.to_dict() for grade in self.grades] if self.grades else [],
            "tasks": [task.to_dict() for task in self.tasks] if self.tasks else [],
            "announcements": (
                [announcement.to_dict() for announcement in self.announcements]
                if self.announcements
                else []
            ),
            "notifications": (
                [notification.to_dict() for notification in self.notifications]
                if self.notifications
                else []
            ),
            "marks": [mark.to_dict() for mark in self.marks] if self.marks else [],
            "events": [event.to_dict() for event in self.events] if self.events else [],
            "roadmaps": (
                [roadmap.to_dict() for roadmap in self.roadmaps]
                if self.roadmaps
                else []
            ),
            "questions": (
                [question.to_dict() for question in self.questions]
                if self.questions
                else []
            ),
            "answers": (
                [answer.to_dict() for answer in self.answers] if self.answers else []
            ),
            "timetables": (
                [timetable.to_dict() for timetable in self.timetables]
                if self.timetables
                else []
            ),
            "reviews": (
                [review.to_dict() for review in self.reviews] if self.reviews else []
            ),
            "going_events": (
                [event.to_dict() for event in self.going_events]
                if self.going_events
                else []
            ),
            "logs": [log.to_dict() for log in self.logs] if self.logs else [],
            "subjects": (
                [subject.to_dict() for subject in self.subjects]
                if self.subjects
                else []
            ),
            "request_limits": (
                [request_limit.to_dict() for request_limit in self.request_limits]
                if self.request_limits
                else []
            ),
        }

    class Model(TypedDict):
        id: int
        name: str
        email: str
        password: str
        phone: str
        gender: str
        type: Optional[str]
        section: Optional[int]
        status: bool
        is_early_access: bool
        manages: dict
        details: dict
        google_id: Optional[str]
        google_name: Optional[str]
        google_email: Optional[str]
        google_avatar: Optional[str]
        google_refresh_token: Optional[str]
        ips: list[str]
        refresh_token: Optional[str]
        refresh_expire_at: Optional[datetime]
        created_at: Optional[datetime]
        updated_at: Optional[datetime]
        year: Optional[Year.Model]
        department: Optional[Department.Model]
        faculty: Optional[Faculty.Model]
        role: Optional[Role.Model]
        pending_user: Optional[PendingUser.Model]
        materials: list[Material.Model]
        # grades: list[Grade.Model]
        tasks: list[Task.Model]
        announcements: list[Announcement.Model]
        notifications: list[Notification.Model]
        # marks: list[Mark.Model]
        # events: list[Event.Model]
        # roadmaps: list[Roadmap.Model]
        # questions: list[Question.Model]
        # answers: list[Answer.Model]
        # timetables: list[Timetable.Model]
        # reviews: list[Review.Model]
        # going_events: list[Event.Model]
        logs: list[Log.Model]
        subjects: list[Subject.Model]
        request_limits: list[RequestLimit.Model]

    # Attributes
    class RefreshToken:
        EXPIRE_DAYS = 30
        MINIMUM_DAYS = 7

    class VerificationToken:
        EXPIRE_HOURS = 1

    class Type:
        MAINSTREAM = "Mainstream"
        CREDIT = "Credit"
