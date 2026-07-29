from pydantic import ValidationError

from core.iControllers.IRoleController import IRoleController
from core.iServices.iRoleService import IRoleService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.responseHandler import ResponseHandler
from core.dtos.roleDtos import AddRoleDto, updateRoleDto


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
            response = await self.role_service.get_role(int(role_id))
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response.data,
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
            response = await self.role_service.get_all()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response.data,
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
            if not isinstance(payload, dict):
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="A JSON object is required",
                )
            try:
                response = await self.role_service.create(AddRoleDto(**payload))
            except ValidationError as exc:
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message=str(exc.errors()[0]["msg"]) if exc.errors() else "Invalid role payload",
                )
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
                code=201,
                data=response.data,
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
            payload = await request.json()
            if not isinstance(payload, dict):
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="A JSON object is required",
                )
            role_id = request.path_params.get("role_id")
            if not role_id:
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Role ID is required",
                )
            try:
                response = await self.role_service.update(
                    updateRoleDto(id=int(role_id), **payload)
                )
            except ValidationError as exc:
                await self.role_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message=str(exc.errors()[0]["msg"]) if exc.errors() else "Invalid role payload",
                )
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
                data=response.data,
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
            response = await self.role_service.delete(int(role_id))
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

    async def get_roles(self, request):
        return await self.find(request)

    async def get_role(self, request):
        return await self.find_one(request)

    async def search_roles(self, request):
        try:
            query = (request.query_params.get("query") or "").strip()
            response = await self.role_service.search_roles(query)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response.data,
            )
        except Exception as e:
            await self.logger.log(
                action="SearchRoles",
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
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response.data,
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
