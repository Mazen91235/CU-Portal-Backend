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
    AssociationProxy,
    association_proxy,
    TYPE_CHECKING,
    mapped_column,
    relationship,
    func,
)

if TYPE_CHECKING:
    from .user import User
    from .exactRole import ExactRole
    from .roleLink import RoleLink


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
    users: Mapped[set["User"]] = relationship(
        "User",
        back_populates="role",
        cascade="all, delete-orphan",
        collection_class=set,
    )
    exact_roles: AssociationProxy[set["ExactRole"]] = association_proxy(
        "role_links",
        "exact_role",
        creator=lambda exact_role: __import__(
            "core.entities.roleLink", fromlist=["RoleLink"]
        ).RoleLink(exact_role=exact_role),
    )
    role_links: Mapped[set["RoleLink"]] = relationship(
        "RoleLink",
        back_populates="role",
        cascade="all, delete-orphan",
        collection_class=set,
    )

    # Versioning
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )

    # Arguments
    __table_args__ = (Index("idx_role_name", func.lower(name), unique=True),)
    __mapper_args__ = {
        "version_id_col": version,
    }

    # Attributes
    class RoleConfig:
        ROLES = [
            "View Admin Panel",
            "View Admin Links",
            "Is Admin",
            "View Faculties",
            "Add Faculties",
            "Edit Faculties",
            "Delete Faculties",
            "Access All Faculties",
            "View Departments",
            "Add Departments",
            "Edit Departments",
            "Delete Departments",
            "Access All Departments",
            "View Years",
            "Add Years",
            "Edit Years",
            "Delete Years",
            "Access All Years",
            "View Users",
            "Manage Users",
            "View Roles",
            "Add Roles",
            "Edit Roles",
            "Delete Roles",
            "Assign Roles",
            "View Courses",
            "Add Courses",
            "Edit Courses",
            "Delete Courses",
            "Access All Courses",
            "View Materials",
            "Add Materials",
            "Edit Materials",
            "Delete Materials",
            "Manage All Materials",
            "View Tasks",
            "Add Tasks",
            "Edit Tasks",
            "Delete Tasks",
            "Manage All Tasks",
            "View Exams",
            "Add Exams",
            "Edit Exams",
            "Delete Exams",
            "Manage All Exams",
            "View Announcements",
            "Add Announcements",
            "Edit Announcements",
            "Delete Announcements",
            "Manage All Announcements",
            "View Weeks",
            "Add Weeks",
            "Edit Weeks",
            "Delete Weeks",
            "View Events",
            "Add Events",
            "Edit Events",
            "Delete Events",
            "Manage All Events",
            "View EventOrganizers",
            "Add EventOrganizers",
            "Edit EventOrganizers",
            "Delete EventOrganizers",
            "View Releases",
            "Add Releases",
            "Edit Releases",
            "Delete Releases",
            "View Logs",
            "Delete Logs",
            "View Messages",
        ]
        EXCLUSIONS = {
            "admin": [],
            "site admin": [
                "View Admin Panel",
                "Is Admin",
                "View Logs",
                "View Messages",
            ],
            "representative": [
                "View Admin Panel",
                "Is Admin",
                "View Logs",
                "View Messages",
                "View Faculties",
                "Add Faculties",
                "Edit Faculties",
                "Delete Faculties",
                "Access All Faculties",
                "View Departments",
                "Add Departments",
                "Edit Departments",
                "Delete Departments",
                "Access All Departments",
                "View Years",
                "Add Years",
                "Edit Years",
                "Delete Years",
                "Access All Years",
            ],
        }
