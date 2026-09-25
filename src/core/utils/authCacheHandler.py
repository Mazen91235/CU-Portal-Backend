from core.entities.attachment import Attachment
from core.entities.exactRole import ExactRole
from core.entities.role import Role
from core.entities.roleLink import RoleLink
from core.entities.user import User


def serialize_user_for_cache(user: User) -> dict:
    """Serialize the user state required by authentication and existing services."""
    data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "gender": user.gender,
        "study_type": user.study_type,
        "section": user.section,
        "status": user.status,
        "is_early_access": user.is_early_access,
        "manages": user.manages,
        "details": user.details,
        "google_id": user.google_id,
        "google_name": user.google_name,
        "google_email": user.google_email,
        "google_avatar": user.google_avatar,
        "google_refresh_token": user.google_refresh_token,
        "ips": user.ips,
        "avatar_id": user.avatar_id,
        "year_id": user.year_id,
        "department_id": user.department_id,
        "faculty_id": user.faculty_id,
        "role_id": user.role_id,
        "version": user.version,
        "registered_subjects": sorted(
            str(subject.id)
            for subject in (getattr(user, "subjects", None) or [])
            if getattr(subject, "id", None) is not None
        ),
    }

    if user.avatar is not None:
        data["avatar"] = {
            "id": user.avatar.id,
            "is_file": user.avatar.is_file,
            "url": user.avatar.url,
            "details": user.avatar.details,
            "author_google_refresh_token": user.avatar.author_google_refresh_token,
            "author_id": user.avatar.author_id,
            "version": user.avatar.version,
        }

    if user.role is not None:
        data["role"] = {
            "id": user.role.id,
            "name": user.role.name,
            "level": user.role.level,
            "version": user.role.version,
            "role_links": [
                {
                    "exact_role": {
                        "id": permission.id,
                        "name": permission.name,
                        "version": permission.version,
                    }
                }
                for permission in (user.role.exact_roles or [])
            ],
        }

    return data


def build_auth_cache(user: User, permissions: set[str]) -> dict:
    return {
        "user": serialize_user_for_cache(user),
        "permissions": sorted(permissions)
    }


def deserialize_user_from_cache(data: dict, refresh_token: str) -> User | None:
    user_data = data.get("user") if isinstance(data, dict) else None
    if not isinstance(user_data, dict) or not user_data.get("id"):
        return None

    scalar_fields = {
        "id",
        "name",
        "email",
        "phone",
        "gender",
        "study_type",
        "section",
        "status",
        "is_early_access",
        "manages",
        "details",
        "google_id",
        "google_name",
        "google_email",
        "google_avatar",
        "google_refresh_token",
        "ips",
        "avatar_id",
        "year_id",
        "department_id",
        "faculty_id",
        "role_id",
        "version",
    }
    user = User(
        **{key: user_data.get(key) for key in scalar_fields if key in user_data}
    )
    user.refresh_token = refresh_token

    avatar_data = user_data.get("avatar")
    if isinstance(avatar_data, dict):
        user.avatar = Attachment(**avatar_data)

    role_data = user_data.get("role")
    permissions = data.get("permissions") or []
    if isinstance(role_data, dict):
        role = Role(
            **{
                key: role_data.get(key)
                for key in ("id", "name", "level", "version")
                if key in role_data
            }
        )
        links = set()
        for link_data in role_data.get("role_links") or []:
            exact_role_data = link_data.get("exact_role") if isinstance(link_data, dict) else None
            if not isinstance(exact_role_data, dict):
                continue
            exact_role = ExactRole(
                **{
                    key: exact_role_data.get(key)
                    for key in ("id", "name", "version")
                    if key in exact_role_data
                }
            )
            links.add(RoleLink(exact_role=exact_role))
        if not links and permissions:
            links = {
                RoleLink(exact_role=ExactRole(name=permission))
                for permission in permissions
            }
        role.role_links = links
        user.role = role

    return user
