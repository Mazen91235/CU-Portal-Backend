from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute, allow_inactive
from core.iControllers.iDepartmentController import IDepartmentController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.departmentDtos import (
    DepartmentCreateDto,
    DepartmentResponseDto,
    DepartmentUpdateDto,
    DepartmentSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_department_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/departments", tags=["User Departments"], route_class=CustomRoute
    )

    def _get_controller() -> IDepartmentController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

    def _get_validation_middleware() -> IValidationMiddleware:
        return validation_middleware_provider()

    async def _is_logged_in(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
        refresh_token: str | None = Depends(cookie_scheme),
    ):
        return await auth_middleware.is_logged_in(request, refresh_token)

    def _is_authorized(*permissions):
        async def authorize(
            request: Request,
            auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
        ):
            return await auth_middleware.is_authorized(request, *permissions)

        return authorize

    def _validate(*keys):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(
                _get_validation_middleware
            ),
        ):
            return await validation_middleware.validate(request, *keys)

        return validate_request

    @router.get(
        "/{department_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(allow_inactive()),
        ],
        status_code=200,
        summary="Find Department",
        description="Find a department by its ID, returning details and summary metrics",
    )
    async def find_one_department(
        department_id: int,
        request: Request,
        controller: IDepartmentController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=department_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(allow_inactive())
        ],
        response_model=BaseResponseDto[list[DepartmentResponseDto]],
        status_code=200,
        summary="Find Departments",
        description="Find departments based on query parameters",
    )
    async def find_departments(
        request: Request,
        query: QueryModel[DepartmentSearchDto] = Depends(
            Parser.parse_query(QueryModel[DepartmentSearchDto])
        ),
        controller: IDepartmentController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)
    
    return router


def create_department_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/departments", tags=["Admin Departments"], route_class=CustomRoute
    )

    def _get_controller() -> IDepartmentController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

    def _get_validation_middleware() -> IValidationMiddleware:
        return validation_middleware_provider()

    async def _is_logged_in(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
        refresh_token: str | None = Depends(cookie_scheme),
    ):
        return await auth_middleware.is_logged_in(request, refresh_token)

    def _is_authorized(*permissions):
        async def authorize(
            request: Request,
            auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
        ):
            return await auth_middleware.is_authorized(request, *permissions)

        return authorize

    def _validate(*keys):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(
                _get_validation_middleware
            ),
        ):
            return await validation_middleware.validate(request, *keys)

        return validate_request

    @router.get(
        "/{department_id}",
        dependencies=[
            Depends(_is_logged_in),
        ],
        status_code=200,
        summary="Find Department",
        description="Find a department by its ID, returning details and summary metrics",
    )
    async def find_one_department(
        department_id: int,
        request: Request,
        controller: IDepartmentController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=department_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
        ],
        response_model=BaseResponseDto[list[DepartmentResponseDto]],
        status_code=200,
        summary="Find Departments",
        description="Find departments based on query parameters",
    )
    async def find_departments(
        request: Request,
        query: QueryModel[DepartmentSearchDto] = Depends(
            Parser.parse_query(QueryModel[DepartmentSearchDto])
        ),
        controller: IDepartmentController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Departments")),
            Depends(_validate("name", "code", "faculty_id", "study_type")),
        ],
        response_model=BaseResponseDto[DepartmentResponseDto],
        status_code=201,
        summary="Create Department",
        description="Create a new department",
    )
    async def create_department(
        data: DepartmentCreateDto,
        request: Request,
        controller: IDepartmentController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{department_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Departments")),
            Depends(_validate("name", "code", "faculty_id", "study_type")),
        ],
        response_model=BaseResponseDto[DepartmentResponseDto],
        status_code=200,
        summary="Update Department",
        description="Update an existing department by its ID",
    )
    async def update_department(
        department_id: int,
        data: DepartmentUpdateDto,
        request: Request,
        controller: IDepartmentController = Depends(_get_controller),
    ):
        return await controller.update(request, id=department_id, data=data)

    @router.delete(
        "/{department_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Departments")),
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Department",
        description="Delete a department by its ID",
    )
    async def delete_department(
        department_id: int,
        request: Request,
        controller: IDepartmentController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=department_id)

    return router
