from sqlalchemy import func

from business.contextVars.userContext import user_context
from core.iServices.iRoleService import IRoleService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.role import Role
from core.entities.exactRole import ExactRole
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.roleDtos import AddRoleDto, updateRoleDto, RoleResponseDto


class RoleService(IRoleService):
    def __init__(
        self,
        role_repository: IBaseRepository[Role],
        logger: IBaseLogger,
        helper_service: IHelperService,
        exact_role_repository: IBaseRepository[ExactRole] | None = None,
    ):
        self.role_repository = role_repository
        self.logger = logger
        self.helper_service = helper_service
        self.exact_role_repository = exact_role_repository

    async def begin_transaction(self):
        await self.role_repository.begin_transaction()

    async def commit_transaction(self):
        await self.role_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.role_repository.rollback_transaction()

    def _build_role_response(self, role: Role) -> RoleResponseDto:
        permissions = [permission.name for permission in getattr(role, "exact_roles", [])]
        return RoleResponseDto(
            id=role.id,
            name=role.name,
            permissions=permissions,
            permission_count=len(permissions),
            level=role.level,
            users_count=len(getattr(role, "users", []) or []),
        )

    def _get_current_user(self):
        return user_context.get(None)

    def _get_current_user_permissions(self) -> list[str]:
        current_user = self._get_current_user()
        if not current_user:
            return []
        role = getattr(current_user, "role", None)
        exact_roles = getattr(role, "exact_roles", None) or []
        return [permission.name for permission in exact_roles if getattr(permission, "name", None)]

    def _validate_permission_shape(self, permissions: list[str] | None):
        if not permissions:
            return True, None, []

        permissions_classified = {}
        seen_pairs = set()
        for permission in permissions:
            if not isinstance(permission, str):
                return False, "Invalid permissions provided", []
            normalized = permission.strip()
            if not normalized:
                continue
            if normalized.lower() == "is admin":
                continue

            if "All" in normalized:
                category = " ".join(normalized.split(" ")[2:]).strip()
                permission_name = " ".join(normalized.split(" ")[:2]).strip()
            else:
                category = " ".join(normalized.split(" ")[1:]).strip()
                permission_name = normalized.split(" ")[0].strip()

            if not category or not permission_name:
                return False, f"Invalid permissions provided: {permission}", []

            pair = (category.lower(), permission_name.lower())
            if pair in seen_pairs:
                return False, f"Duplicate permissions provided: {permission}", []
            seen_pairs.add(pair)
            permissions_classified.setdefault(category, []).append(permission_name)

        for category, permission_names in permissions_classified.items():
            if not any(permission_name.lower().startswith("view") for permission_name in permission_names):
                return False, f"You can't assign permissions to '{category}' without assigning the 'View' permission", []

        return True, None, permissions

    def _validate_current_user_can_access_permissions(self, permissions: list[str] | None):
        current_user_permissions = set(self._get_current_user_permissions())
        if not current_user_permissions:
            return True, []
        missing_permissions = [permission for permission in permissions or [] if permission not in current_user_permissions]
        return not missing_permissions, missing_permissions

    def _get_role_visibility_predicate(self):
        current_user = self._get_current_user()
        if not current_user:
            return None
        role = getattr(current_user, "role", None)
        if role is None or getattr(role, "level", None) is None:
            return None
        return Role.level >= role.level

    async def _validate_permissions(self, permissions: list[str] | None):
        if not permissions:
            return True, []

        is_valid, error_message, normalized_permissions = self._validate_permission_shape(permissions)
        if not is_valid:
            return False, [error_message]

        can_assign, missing_permissions = self._validate_current_user_can_access_permissions(
            normalized_permissions
        )
        return can_assign, missing_permissions

    async def _resolve_permissions(self, permissions: list[str] | None):
        if not permissions:
            return []
        if self.exact_role_repository is None:
            return []
        resolved_permissions = []
        for permission in permissions:
            existing_permission = await self.exact_role_repository.find_one(
                func.lower(ExactRole.name) == permission.lower()
            )
            if existing_permission.success and existing_permission.data:
                resolved_permissions.append(existing_permission.data)
            else:
                await self.logger.log(
                    action="ResolvePermissions",
                    entity="Role",
                    level="warning",
                    code=404,
                    message="Permission not found",
                    details={"permission": permission},
                    source="RoleService",
                )
                return None
        return resolved_permissions

    async def create(self, data: AddRoleDto):
        try:
            existing_role = await self.role_repository.find_one(
                func.lower(Role.name) == data.name.lower()
            )
            if existing_role.success and existing_role.data:
                await self.logger.log(
                    action="Add",
                    entity="Role",
                    level="warning",
                    code=400,
                    message="Role with this name already exists",
                    details={"role_name": data.name},
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Role with this name already exists",
                    data=None,
                )

            if data.permissions is not None:
                can_assign, missing_permissions = await self._validate_permissions(data.permissions)
                if not can_assign:
                    return BaseResponseDto(
                        success=False,
                        code=403,
                        message="You cannot assign permissions you don't have",
                        data=None,
                    )

            permissions = await self._resolve_permissions(data.permissions)
            if permissions is None:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="One or more permissions were not found",
                    data=None,
                )

            role = Role(name=data.name.strip(), level=3)
            role.exact_roles = permissions
            created_role = await self.role_repository.create(role)
            if not created_role.success or not created_role.data:
                return BaseResponseDto(
                    success=False,
                    code=created_role.code or 500,
                    message=created_role.message or "Failed to create role",
                    data=None,
                )

            await self.logger.log(
                action="Add",
                entity="Role",
                level="info",
                code=201,
                message="Role created successfully",
                details={"role_name": data.name},
                source="RoleService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=self._build_role_response(created_role.data),
                message="Role created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Add",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while creating role",
                details={"error": str(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating role",
            )

    async def update(self, data: updateRoleDto):
        try:
            if not data.id:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Role ID is required",
                )

            existing_role_response = await self.role_repository.find_one(
                Role.id == data.id,
                includes=["exact_roles", "users"],
            )
            if not existing_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_role_response.code,
                    data=None,
                    message=existing_role_response.message,
                )
            role = existing_role_response.data
            if not role:
                return BaseResponseDto(success=False, code=404, data=None, message="Role not found")

            if data.name is not None:
                duplicate_role = await self.role_repository.find_one(
                    func.lower(Role.name) == data.name.lower()
                )
                if duplicate_role.success and duplicate_role.data and duplicate_role.data.id != data.id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Role with this name already exists",
                    )
                role.name = data.name.strip()

            if data.permissions is not None:
                can_assign, missing_permissions = await self._validate_permissions(data.permissions)
                if not can_assign:
                    error_message = missing_permissions[0] if missing_permissions else "You cannot assign permissions you don't have"
                    return BaseResponseDto(
                        success=False,
                        code=403 if missing_permissions else 400,
                        message=error_message,
                        data=None,
                    )

                can_access, role_missing_permissions = self._validate_current_user_can_access_permissions(
                    [permission.name for permission in getattr(role, "exact_roles", []) or []]
                )
                if not can_access:
                    return BaseResponseDto(
                        success=False,
                        code=403,
                        message="You cannot update a role having permissions you don't have",
                        data=None,
                    )

                permissions = await self._resolve_permissions(data.permissions)
                if permissions is None:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        message="One or more permissions were not found",
                        data=None,
                    )
                role.exact_roles = permissions

            updated_role = await self.role_repository.update(role)
            if not updated_role.success or not updated_role.data:
                return BaseResponseDto(
                    success=False,
                    code=updated_role.code or 500,
                    data=None,
                    message=updated_role.message or "Failed to update role",
                )

            await self.logger.log(
                action="Edit",
                entity="Role",
                level="info",
                code=200,
                message="Role updated successfully",
                details={"role_id": data.id},
                source="RoleService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=self._build_role_response(updated_role.data),
                message="Role updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Edit",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while updating role",
                details={"error": str(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating role",
            )

    async def delete(self, role_id: int):
        try:
            role_response = await self.role_repository.find_one(
                Role.id == role_id,
                includes=["users", "exact_roles"],
            )
            if not role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=role_response.code,
                    data=False,
                    message=role_response.message,
                )
            role = role_response.data
            if not role:
                return BaseResponseDto(success=False, code=404, data=False, message="Role not found")
            if getattr(role, "users", None):
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="Role cannot be deleted because it has users associated with it",
                )

            can_access, role_missing_permissions = self._validate_current_user_can_access_permissions(
                [permission.name for permission in getattr(role, "exact_roles", []) or []]
            )
            if not can_access:
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=False,
                    message="You cannot delete a role having permissions you don't have",
                )

            role.exact_roles.clear()
            delete_response = await self.role_repository.delete(role)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=False,
                    message=delete_response.message,
                )
            return BaseResponseDto(success=True, code=200, data=True, message="Role deleted successfully")
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while deleting role",
                details={"error": str(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while deleting role",
            )

    async def get_role(self, role_id: int):
        try:
            role_response = await self.role_repository.find_one(
                Role.id == role_id,
                includes=["exact_roles", "users"],
            )
            if not role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=role_response.code,
                    data=None,
                    message=role_response.message,
                )
            role = role_response.data
            if not role:
                return BaseResponseDto(success=False, code=404, data=None, message="Role not found")

            can_access, role_missing_permissions = self._validate_current_user_can_access_permissions(
                [permission.name for permission in getattr(role, "exact_roles", []) or []]
            )
            if not can_access:
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You cannot view a role having permissions you don't have",
                )

            return BaseResponseDto(
                success=True,
                code=200,
                data=self._build_role_response(role),
                message="Role retrieved successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Get",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while retrieving role",
                details={"error": str(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while retrieving role",
            )

    async def search_roles(self, query: str):
        try:
            if not query:
                return await self.get_all()
            predicate = self._get_role_visibility_predicate()
            if predicate is not None:
                predicate = predicate & func.lower(Role.name).startswith(query.lower())
            else:
                predicate = func.lower(Role.name).startswith(query.lower())
            role_response = await self.role_repository.find(
                predicate,
                includes=["exact_roles", "users"],
                order_by=[Role.name],
            )
            if not role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=role_response.code,
                    data=[],
                    message=role_response.message,
                )
            roles = role_response.data or []
            return BaseResponseDto(
                success=True,
                code=200,
                data=[self._build_role_response(role) for role in roles],
                message="Roles search completed successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Search",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while searching roles",
                details={"error": str(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=[],
                message="An error occurred while searching roles",
            )

    async def get_all(self):
        try:
            predicate = self._get_role_visibility_predicate()
            role_response = await self.role_repository.find(
                predicate,
                includes=["exact_roles", "users"],
                order_by=[Role.name],
            )
            if not role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=role_response.code,
                    data=[],
                    message=role_response.message,
                )
            roles = role_response.data or []
            return BaseResponseDto(
                success=True,
                code=200,
                data=[self._build_role_response(role) for role in roles],
                message="Roles retrieved successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Get",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while retrieving roles",
                details={"error": str(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=[],
                message="An error occurred while retrieving roles",
            )

    async def count_permissions(self):
        try:
            if self.exact_role_repository is None:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=0,
                    message="Permission repository is not configured",
                )
            count_response = await self.exact_role_repository.count()
            if not count_response.success:
                return BaseResponseDto(
                    success=False,
                    code=count_response.code,
                    data=0,
                    message=count_response.message,
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=count_response.data,
                message="Permissions count retrieved successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Count",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while counting permissions",
                details={"error": str(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=0,
                message="An error occurred while counting permissions",
            )
