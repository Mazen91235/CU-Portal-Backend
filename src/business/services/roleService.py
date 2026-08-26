import math
from sqlalchemy import func
from business.contextVars.userContext import user_context
from core.iServices.iRoleService import IRoleService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.role import Role
from core.entities.exactRole import ExactRole
from core.dtos.baseDtos import BaseResponseDto


class RoleService(IRoleService):
    def __init__(
        self,
        role_repository: IBaseRepository[Role],
        exact_role_repository: IBaseRepository[ExactRole],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.role_repository = role_repository
        self.exact_role_repository = exact_role_repository
        self.logger = logger
        self.helper_service = helper_service

    async def begin_transaction(self):
        await self.role_repository.begin_transaction()

    async def commit_transaction(self):
        await self.role_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.role_repository.rollback_transaction()

    # CRUD Functions
    async def find_one(
        self,
        data=None,
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                Role, data, ["name"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Role, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Role", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Role", order_by
            )

            result = await self.role_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
            )

            if not result.success:
                return BaseResponseDto(
                    success=False, code=result.code, data=None, message=result.message
                )

            role = result.data

            return BaseResponseDto(success=True, code=200, data=role)

        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Role",
                level="error",
                code=500,
                message="Error finding role",
                details={"error": repr(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding the role",
            )

    async def find(
        self,
        data=None,
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
        page=1,
        limit=50,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                Role, data, ["name"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Role, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Role", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Role", order_by
            )

            result = await self.role_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
                page,
                limit,
            )

            if not result.success:
                return BaseResponseDto(
                    success=False, code=result.code, data=None, message=result.message
                )
            roles = result.data
            return BaseResponseDto(
                success=True, code=200, data=roles, next_page=result.next_page
            )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while finding roles",
                details={"error": repr(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding roles",
            )

    async def create(self, data):
        try:
            existing_role_response = await self.role_repository.find_one(
                Role.name == data.name
            )
            if not existing_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_role_response.code,
                    data=None,
                    message=existing_role_response.message,
                )
            existing_role = existing_role_response.data
            if existing_role:
                await self.logger.log(
                    action="Create",
                    entity="Role",
                    level="warning",
                    code=400,
                    message="Role with the same name already exists.",
                    details={"name": data.name},
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Role with the same name already exists.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Role",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Role Creation.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating role",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Create",
                    entity="Role",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Role Creation.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating role",
                )
            if not set(data.permissions or []).issubset(
                set(logged_in_user_permissions)
            ):
                await self.logger.log(
                    action="Create",
                    entity="Role",
                    level="warning",
                    code=403,
                    message="User does not have permission to assign one or more of the specified permissions.",
                    details={"permissions": data.permissions},
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to assign one or more of the specified permissions.",
                )
            validate_permissions_response = await self._validate_permissions(
                data.permissions or []
            )
            if not validate_permissions_response.success:
                return BaseResponseDto(
                    success=False,
                    code=validate_permissions_response.code,
                    data=None,
                    message=validate_permissions_response.message,
                )
            exact_roles = set()
            for permission in data.permissions or []:
                exact_role_response = await self.exact_role_repository.find_one(
                    ExactRole.name == permission
                )
                if not exact_role_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=exact_role_response.code,
                        data=None,
                        message=exact_role_response.message,
                    )
                exact_role = exact_role_response.data
                if not exact_role:
                    await self.logger.log(
                        action="Create",
                        entity="Role",
                        level="warning",
                        code=404,
                        message=f"Exact role '{permission}' not found.",
                        source="RoleService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Exact role '{permission}' not found.",
                    )
                exact_roles.add(exact_role)
            role = Role(
                name=data.name,
                level=3,
                exact_roles=exact_roles,
            )
            create_role_response = await self.role_repository.create(role)
            if not create_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_role_response.code,
                    data=None,
                    message=create_role_response.message,
                )
            created_role = create_role_response.data
            if not created_role:
                await self.logger.log(
                    action="Create",
                    entity="Role",
                    level="error",
                    code=500,
                    message="Failed to create role without a specific error.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating role",
                )
            await self.logger.log(
                action="Create",
                entity="Role",
                level="info",
                code=201,
                message="Role created successfully",
                source="RoleService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_role,
                message="Role created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while creating role",
                details={"error": repr(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating role",
            )

    async def update(self, id, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Role, ["role_links.exact_role"]
            )
            target_role_response = await self.role_repository.find_one(
                Role.id == id, dynamic_includes
            )
            if not target_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_role_response.code,
                    data=None,
                    message=target_role_response.message,
                )
            target_role = target_role_response.data
            if not target_role:
                await self.logger.log(
                    action="Update",
                    entity="Role",
                    level="info",
                    code=404,
                    message="Role not found for update",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Role not found",
                )
            existing_role_response = await self.role_repository.find_one(
                Role.name == data.name
            )
            if not existing_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_role_response.code,
                    data=None,
                    message=existing_role_response.message,
                )
            existing_role = existing_role_response.data
            if existing_role and existing_role.id != id:
                await self.logger.log(
                    action="Update",
                    entity="Role",
                    level="warning",
                    code=400,
                    message="Another role with the same name already exists for this subject.",
                    details={"name": data.name},
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Another role with the same name already exists for this subject.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Role",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Role Update.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating role",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Update",
                    entity="Role",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Role Update.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating role",
                )
            if not set(data.permissions or []).issubset(
                set(logged_in_user_permissions)
            ):
                await self.logger.log(
                    action="Update",
                    entity="Role",
                    level="warning",
                    code=403,
                    message="User does not have permission to assign one or more of the specified permissions.",
                    details={"permissions": data.permissions},
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to assign one or more of the specified permissions.",
                )
            role_permissions = [perm.name for perm in target_role.exact_roles]
            if not set(role_permissions).issubset(set(logged_in_user_permissions)):
                await self.logger.log(
                    action="Update",
                    entity="Role",
                    level="warning",
                    code=403,
                    message="User does not have permission to assign one or more of the specified permissions.",
                    details={"permissions": role_permissions},
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to assign one or more of the specified permissions.",
                )
            validate_permissions_response = await self._validate_permissions(
                data.permissions or []
            )
            if not validate_permissions_response.success:
                return BaseResponseDto(
                    success=False,
                    code=validate_permissions_response.code,
                    data=None,
                    message=validate_permissions_response.message,
                )
            exact_roles = set()
            for permission in data.permissions or []:
                exact_role_response = await self.exact_role_repository.find_one(
                    ExactRole.name == permission
                )
                if not exact_role_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=exact_role_response.code,
                        data=None,
                        message=exact_role_response.message,
                    )
                exact_role = exact_role_response.data
                if not exact_role:
                    await self.logger.log(
                        action="Update",
                        entity="Role",
                        level="warning",
                        code=404,
                        message=f"Exact role '{permission}' not found.",
                        source="RoleService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Exact role '{permission}' not found.",
                    )
                exact_roles.add(exact_role)
            target_role.name = data.name or ""
            target_role.exact_roles = exact_roles
            update_response = await self.role_repository.update(
                target_role, ["name", "role_links"]
            )
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_role = update_response.data
            if not updated_role:
                await self.logger.log(
                    action="Update",
                    entity="Role",
                    level="error",
                    code=500,
                    message="Failed to update role without a specific error.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating role",
                )
            await self.logger.log(
                action="Update",
                entity="Role",
                level="info",
                code=200,
                message="Role updated successfully",
                source="RoleService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_role,
                message="Role updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while updating role",
                details={"error": repr(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating role",
            )

    async def delete(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Role, ["users", "role_links.exact_role"]
            )
            target_role_response = await self.role_repository.find_one(
                Role.id == data.id, dynamic_includes
            )
            if not target_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_role_response.code,
                    data=None,
                    message=target_role_response.message,
                )
            target_role = target_role_response.data
            if not target_role:
                await self.logger.log(
                    action="Delete",
                    entity="Role",
                    level="warning",
                    code=404,
                    message="Role not found for deletion",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Role not found",
                )
            if target_role.users and len(target_role.users) > 0:
                await self.logger.log(
                    action="Delete",
                    entity="Role",
                    level="warning",
                    code=400,
                    message="Cannot delete role with associated users.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Cannot delete role with associated users.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Role",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Role Deletion.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting role",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Delete",
                    entity="Role",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Role Deletion.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting role",
                )
            role_permissions = [perm.name for perm in target_role.exact_roles]
            if not set(role_permissions).issubset(set(logged_in_user_permissions)):
                await self.logger.log(
                    action="Delete",
                    entity="Role",
                    level="warning",
                    code=403,
                    message="User does not have permission to delete this role.",
                    details={"permissions": role_permissions},
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to delete this role.",
                )
            delete_response = await self.role_repository.delete(target_role)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            await self.logger.log(
                action="Delete",
                entity="Role",
                level="info",
                code=200,
                message="Role deleted successfully",
                source="RoleService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Role deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while deleting role",
                details={"error": repr(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting role",
            )

    # Role Specific Functions
    async def count_permissions(self):
        try:
            count_response = await self.exact_role_repository.count()
            if not count_response.success:
                return BaseResponseDto(
                    success=False,
                    code=count_response.code,
                    data=None,
                    message=count_response.message,
                )
            permission_count = count_response.data
            return BaseResponseDto(
                success=True,
                code=200,
                data=permission_count,
                message="Successfully counted permissions",
            )
        except Exception as ex:
            await self.logger.log(
                action="CountPermissions",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while counting permissions",
                details={"error": repr(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while counting permissions",
            )

    async def reset_permissions(self):
        try:
            current_exact_roles_response = await self.exact_role_repository.find(
                limit=math.floor(1e6)
            )
            if not current_exact_roles_response.success:
                return BaseResponseDto(
                    success=False,
                    code=current_exact_roles_response.code,
                    data=None,
                    message=current_exact_roles_response.message,
                )
            current_exact_roles = current_exact_roles_response.data
            if not current_exact_roles:
                await self.logger.log(
                    action="ResetPermissions",
                    entity="Role",
                    level="warning",
                    code=404,
                    message="No exact roles found to reset permissions.",
                    source="RoleService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="No exact roles found to reset permissions.",
                )
            all_exact_roles = {perm.name: perm for perm in current_exact_roles}
            current_permission_names = [perm.name for perm in current_exact_roles]
            required_permissions = Role.RoleConfig.ROLES
            permissions_to_add = set(required_permissions) - set(
                current_permission_names
            )
            for permission in permissions_to_add:
                new_exact_role = ExactRole(name=permission)
                create_response = await self.exact_role_repository.create(
                    new_exact_role
                )
                if not create_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=create_response.code,
                        data=None,
                        message=create_response.message,
                    )
                created_exact_role = create_response.data
                if not created_exact_role:
                    await self.logger.log(
                        action="ResetPermissions",
                        entity="Role",
                        level="error",
                        code=500,
                        message=f"Failed to create exact role '{permission}' without a specific error.",
                        source="RoleService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message=f"An error occurred while creating exact role '{permission}'",
                    )
                all_exact_roles[permission] = created_exact_role
            permissions_to_remove = set(current_permission_names) - set(
                required_permissions
            )
            for permission in permissions_to_remove:
                exact_role_to_remove_response = (
                    await self.exact_role_repository.find_one(
                        ExactRole.name == permission
                    )
                )
                if not exact_role_to_remove_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=exact_role_to_remove_response.code,
                        data=None,
                        message=exact_role_to_remove_response.message,
                    )
                exact_role_to_remove = exact_role_to_remove_response.data
                if not exact_role_to_remove:
                    await self.logger.log(
                        action="ResetPermissions",
                        entity="Role",
                        level="warning",
                        code=404,
                        message=f"Exact role '{permission}' not found for removal.",
                        source="RoleService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Exact role '{permission}' not found for removal.",
                    )
                delete_response = await self.exact_role_repository.delete(
                    exact_role_to_remove
                )
                if not delete_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=delete_response.code,
                        data=None,
                        message=delete_response.message,
                    )
                all_exact_roles.pop(permission, None)
            exclusions = Role.RoleConfig.EXCLUSIONS
            for exclusion_role, excluded_permissions in exclusions.items():
                role_required_permissions = set(required_permissions) - set(
                    excluded_permissions
                )
                dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Role, ["role_links.exact_role"]
                )
                role_response = await self.role_repository.find_one(
                    Role.name == exclusion_role, dynamic_includes
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
                    level = 2 if exclusion_role != "admin" else 1
                    role = Role(name=exclusion_role, level=level)
                    for permission in role_required_permissions:
                        exact_role = all_exact_roles.get(permission)
                        if not exact_role:
                            await self.logger.log(
                                action="ResetPermissions",
                                entity="Role",
                                level="warning",
                                code=404,
                                message=f"Exact role '{permission}' not found for addition to role '{exclusion_role}'.",
                                source="RoleService",
                            )
                            return BaseResponseDto(
                                success=False,
                                code=404,
                                data=None,
                                message=f"Exact role '{permission}' not found for addition to role '{exclusion_role}'.",
                            )
                        role.exact_roles.add(exact_role)
                    create_role_response = await self.role_repository.create(role)
                    if not create_role_response.success:
                        return BaseResponseDto(
                            success=False,
                            code=create_role_response.code,
                            data=None,
                            message=create_role_response.message,
                        )
                    role = create_role_response.data
                    if not role:
                        await self.logger.log(
                            action="ResetPermissions",
                            entity="Role",
                            level="error",
                            code=500,
                            message=f"Failed to create role '{exclusion_role}' without a specific error.",
                            source="RoleService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=500,
                            data=None,
                            message=f"An error occurred while creating role '{exclusion_role}'",
                        )
                else:
                    role_current_permissions = [perm.name for perm in role.exact_roles]
                    role_permissions_to_add = set(role_required_permissions) - set(
                        role_current_permissions
                    )
                    role_permissions_to_remove = set(role_current_permissions) - set(
                        role_required_permissions
                    )
                    for permission in role_permissions_to_add:
                        exact_role = all_exact_roles.get(permission)
                        if not exact_role:
                            await self.logger.log(
                                action="ResetPermissions",
                                entity="Role",
                                level="warning",
                                code=404,
                                message=f"Exact role '{permission}' not found for addition to role '{exclusion_role}'.",
                                source="RoleService",
                            )
                            return BaseResponseDto(
                                success=False,
                                code=404,
                                data=None,
                                message=f"Exact role '{permission}' not found for addition to role '{exclusion_role}'.",
                            )
                        role.exact_roles.add(exact_role)
                    for permission in role_permissions_to_remove:
                        exact_role = all_exact_roles.get(permission)
                        if not exact_role:
                            await self.logger.log(
                                action="ResetPermissions",
                                entity="Role",
                                level="warning",
                                code=404,
                                message=f"Exact role '{permission}' not found for removal from role '{exclusion_role}'.",
                                source="RoleService",
                            )
                            return BaseResponseDto(
                                success=False,
                                code=404,
                                data=None,
                                message=f"Exact role '{permission}' not found for removal from role '{exclusion_role}'.",
                            )
                        role.exact_roles.remove(exact_role)
                    update_response = await self.role_repository.update(
                        role, ["role_links", "exact_roles"]
                    )
                    if not update_response.success:
                        return BaseResponseDto(
                            success=False,
                            code=update_response.code,
                            data=None,
                            message=update_response.message,
                        )
                    updated_role = update_response.data
                    if not updated_role:
                        await self.logger.log(
                            action="ResetPermissions",
                            entity="Role",
                            level="error",
                            code=500,
                            message=f"Failed to update role '{exclusion_role}' without a specific error.",
                            source="RoleService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=500,
                            data=None,
                            message=f"An error occurred while updating role '{exclusion_role}'",
                        )
            await self.logger.log(
                action="ResetPermissions",
                entity="Role",
                level="info",
                code=200,
                message=f"Successfully reset permissions",
                source="RoleService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                message=f"Successfully reset permissions",
            )
        except Exception as ex:
            await self.logger.log(
                action="ResetPermissions",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while resetting permissions",
                details={"error": repr(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while resetting permissions",
            )

    # Helper Functions
    async def _validate_permissions(self, permissions: list[str]) -> BaseResponseDto:
        try:
            categories = {}
            for permission in permissions:
                category = permission.split(" ")[-1]
                if category not in categories:
                    categories[category] = []
                categories[category].append(" ".join(permission.split(" ")[:-1]))
            for category, perms in categories.items():
                if "View" not in perms:
                    await self.logger.log(
                        action="ValidatePermissions",
                        entity="Role",
                        level="warning",
                        code=400,
                        message=f"Missing 'View' permission for category '{category}'",
                        details={"permissions": permissions},
                        source="RoleService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        message=f"Missing 'View' permission for category '{category}'",
                    )
            return BaseResponseDto(success=True, code=200)
        except Exception as ex:
            await self.logger.log(
                action="ValidatePermissions",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while validating permissions",
                details={"error": repr(ex)},
                source="RoleService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                message="An error occurred while validating permissions",
            )
