from pydantic import ValidationError

from core.iControllers.iRoleController import IRoleController
from core.iServices.iRoleService import IRoleService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.entities.role import Role
from core.dtos.roleDtos import (
    RoleCreateDto,
    RoleResponseDto,
    RoleUpdateDto,
    RoleDeleteDto,
    RoleSearchDto,
)
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser
from core.utils.responseHandler import ResponseHandler
from core.models.queryModel import QueryModel


class RoleController(IRoleController):
    def __init__(self, role_service: IRoleService, logger: IBaseLogger):
        self.role_service = role_service
        self.logger = logger

    async def find_one(self, request):
        try:
            role_id = request.path_params.get("role_id")
            if not role_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Role ID is required",
                )

            entity_search_dto = Generator[RoleSearchDto].generate(
                RoleSearchDto, {"id": int(role_id)}
            )

            response = await self.role_service.find_one(
                entity_search_dto,
                [
                    "exact_roles",
                    "users",
                ],
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            role = response.data
            if not role:
                await self.logger.log(
                    action="FindOne",
                    entity="Role",
                    level="info",
                    code=404,
                    message="Role not found",
                    details={"role_id": role_id},
                    source="RoleController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Role not found",
                )
            mapped_role = Mapper[Role, RoleResponseDto].map(role, RoleResponseDto, True)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=mapped_role,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="RoleController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request):
        try:
            query = Parser.parse_query(
                request.query_params.get("query", "{}"),
                QueryModel[RoleSearchDto],
            )
            entity_search_dto = Generator[RoleSearchDto].generate_from_query(
                RoleSearchDto, query
            )

            includes = query.includes
            selects = query.selects
            is_and = query.is_and
            starts_with = query.starts_with
            is_exact = query.is_exact
            order_by = query.order_by
            descending = query.descending
            page = query.page or 1
            limit = query.limit or 50

            response = await self.role_service.find(
                entity_search_dto,
                includes,
                selects,
                is_and,
                starts_with,
                is_exact,
                order_by,
                descending,
                page,
                limit,
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            roles = response.data

            if not roles:
                await self.logger.log(
                    action="Find",
                    entity="Role",
                    level="info",
                    code=404,
                    message="Roles not found",
                    source="RoleController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Roles not found",
                )

            roles_mapped = Mapper[Role, RoleResponseDto].map_list(
                roles, RoleResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=roles_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="RoleController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request):
        try:
            await self.role_service.begin_transaction()
            payload = await request.json()
            data = Generator[RoleCreateDto].generate(RoleCreateDto, payload)

            response = await self.role_service.create(data)

            if not response.success:
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            created_role = response.data
            if not created_role:
                await self.role_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Role",
                    level="error",
                    code=500,
                    message="Failed to create role",
                    details={},
                    source="RoleController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create role",
                )

            role_mapped = Mapper[Role, RoleResponseDto].map(
                created_role, RoleResponseDto, True
            )

            await self.role_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=role_mapped,
                message="Role created successfully",
            )
        except Exception as e:
            await self.role_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="RoleController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request):
        try:
            await self.role_service.begin_transaction()
            role_id = request.path_params.get("role_id")

            if not role_id:
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Role ID is required",
                )

            payload = await request.json()
            payload["id"] = int(role_id)
            data = Generator[RoleUpdateDto].generate(RoleUpdateDto, payload)

            response = await self.role_service.update(data)

            if not response.success:
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_role = response.data
            if not updated_role:
                await self.role_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Role",
                    level="error",
                    code=500,
                    message="Failed to update role",
                    details={},
                    source="RoleController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to update role",
                )
            role_mapped = Mapper[Role, RoleResponseDto].map(
                updated_role, RoleResponseDto, True
            )

            await self.role_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=role_mapped,
                message="Role updated successfully",
            )

        except Exception as e:
            await self.role_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="RoleController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request):
        try:
            await self.role_service.begin_transaction()
            role_id = request.path_params.get("role_id")

            if not role_id:
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Role ID is required",
                )

            data = Generator[RoleDeleteDto].generate(
                RoleDeleteDto, {"id": int(role_id)}
            )
            entity = Mapper[RoleDeleteDto, Role].map(data, Role)

            response = await self.role_service.delete(entity)

            if not response.success:
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.role_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Role deleted successfully",
            )

        except Exception as e:
            await self.role_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="RoleController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def count_permissions(self, request):
        try:
            response = await self.role_service.count_permissions()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            permission_count = response.data
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=permission_count,
            )
        except Exception as e:
            await self.logger.log(
                action="CountPermissions",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="RoleController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def reset_permissions(self, request):
        try:
            response = await self.role_service.reset_permissions()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Permissions reset successfully",
            )
        except Exception as e:
            await self.logger.log(
                action="ResetPermissions",
                entity="Role",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="RoleController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
