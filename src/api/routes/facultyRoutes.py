from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iFacultyController import IFacultyController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.facultyDtos import (
    FacultyCreateDto,
    FacultyResponseDto,
    FacultyUpdateDto,
    FacultySearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_faculty_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/faculties", tags=["Admin Faculties"], route_class=CustomRoute
    )

    def _get_controller() -> IFacultyController:
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
        "/{faculty_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Faculties")),
        ],
        response_model=BaseResponseDto[FacultyResponseDto],
        status_code=200,
        summary="Find Faculty",
        description="Get a single faculty by its ID",
    )
    async def find_one_faculty(
        faculty_id: int,
        request: Request,
        controller: IFacultyController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=faculty_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Faculties")),
        ],
        response_model=BaseResponseDto[list[FacultyResponseDto]],
        status_code=200,
        summary="Find Faculties",
        description="Get all faculties matching optional filter criteria",
    )
    async def find_faculties(
        request: Request,
        query: QueryModel[FacultySearchDto] = Depends(
            Parser.parse_query(QueryModel[FacultySearchDto])
        ),
        controller: IFacultyController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Faculties")),
            Depends(_validate("name")),
        ],
        response_model=BaseResponseDto[FacultyResponseDto],
        status_code=201,
        summary="Create Faculty",
        description="Create a new faculty",
    )
    async def create_faculty(
        data: FacultyCreateDto,
        request: Request,
        controller: IFacultyController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{faculty_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Faculties")),
            Depends(_validate("name")),
        ],
        response_model=BaseResponseDto[FacultyResponseDto],
        status_code=200,
        summary="Update Faculty",
        description="Update an existing faculty",
    )
    async def update_faculty(
        faculty_id: int,
        data: FacultyUpdateDto,
        request: Request,
        controller: IFacultyController = Depends(_get_controller),
    ):
        return await controller.update(request, id=faculty_id, data=data)

    @router.delete(
        "/{faculty_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Faculties")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Delete Faculty",
        description="Delete an existing faculty",
    )
    async def delete_faculty(
        faculty_id: int,
        request: Request,
        controller: IFacultyController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=faculty_id)

    return router
