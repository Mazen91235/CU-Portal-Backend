from fastapi import APIRouter, Request, Depends

from core.iControllers.iRoleController import IRoleController
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
        "/{role_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Roles"))],
        response_model=BaseResponseDto[RoleResponseDto],
        status_code=200,
        summary="Find role by ID",
        description="Retrieve a single role by its ID",
    )
    async def find_one(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Roles"))],
        response_model=BaseResponseDto[list[RoleResponseDto]],
        status_code=200,
        summary="Find Roles by Query",
        description="Retrieve a list of roles based on query parameters",
    )
    async def find(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.find(request)

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

    @router.get(
        "/permissions/reset",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("Is Admin"))],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Reset permissions",
        description="Reset the available permissions in the system",
    )
    async def reset_permissions(
        request: Request, controller: IRoleController = Depends(_get_controller)
    ):
        return await controller.reset_permissions(request)

    return router
