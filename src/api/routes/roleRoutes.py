from fastapi import APIRouter, Request, Depends

from core.iControllers.IRoleController import IRoleController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.roleDtos import RoleResponseDto


def create_role_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/roles", tags=["Roles"])

    def _get_controller() -> IRoleController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

    def _get_validation_middleware() -> IValidationMiddleware:
        return validation_middleware_provider()

    async def _is_logged_in(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
    ):
        return await auth_middleware.is_logged_in(request)

    def _is_authorized(*permissions):
        async def authorize(
            request: Request,
            auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
        ):
            return await auth_middleware.is_authorized(request, *permissions)

        return authorize

    @router.get(
        "/permissions/count",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Roles"))],
        response_model=BaseResponseDto[int],
        status_code=200,
        summary="Count permissions",
        description="Count the available exact permissions in the system",
    )
    async def count_permissions(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.count_permissions(request)

    @router.post(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("Add Roles"))],
        response_model=BaseResponseDto[RoleResponseDto],
        status_code=201,
        summary="Create a role",
        description="Create a new role with the provided name and permissions",
    )
    async def create(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/{role_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("Edit Roles"))],
        response_model=BaseResponseDto[RoleResponseDto],
        status_code=200,
        summary="Update a role",
        description="Update an existing role by its ID",
    )
    async def update(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.update(request)

    @router.delete(
        "/{role_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("Delete Roles"))],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete a role",
        description="Delete an existing role by its ID",
    )
    async def delete(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.delete(request)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Roles"))],
        response_model=BaseResponseDto[list[RoleResponseDto]],
        status_code=200,
        summary="Get all roles",
        description="Retrieve all roles visible to the current user",
    )
    async def get_roles(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.get_roles(request)

    @router.get(
        "/{role_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Roles"))],
        response_model=BaseResponseDto[RoleResponseDto],
        status_code=200,
        summary="Get role by ID",
        description="Retrieve a single role by its ID",
    )
    async def get_role(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.get_role(request)

    @router.get(
        "/search",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Roles"))],
        response_model=BaseResponseDto[list[RoleResponseDto]],
        status_code=200,
        summary="Search roles",
        description="Search roles by name",
    )
    async def search_roles(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.search_roles(request)

    return router
