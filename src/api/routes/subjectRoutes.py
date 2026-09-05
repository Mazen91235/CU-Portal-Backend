from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iSubjectController import ISubjectController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.subjectDtos import (
    SubjectCreateDto,
    SubjectResponseDto,
    SubjectUpdateDto,
    SubjectSearchDto,
    SubjectSearchAvailableDto,
)
from core.dtos.userSubjectLinkDtos import UserSubjectLinkActionDto
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_subject_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/courses", tags=["User Courses"], route_class=CustomRoute
    )

    def _get_controller() -> ISubjectController:
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

    async def _is_ready(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
    ):
        return await auth_middleware.is_ready(request)

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
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[list[SubjectResponseDto]],
        status_code=200,
        summary="Get Available Courses",
        description="Get courses available for the current user to register",
    )
    async def get_available_subjects(
        request: Request,
        query: QueryModel[SubjectSearchAvailableDto] = Depends(
            Parser.parse_query(QueryModel[SubjectSearchAvailableDto])
        ),
        controller: ISubjectController = Depends(_get_controller),
    ):
        return await controller.get_available(request, query=query)

    @router.get(
        "/enrolled",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[list[SubjectResponseDto]],
        status_code=200,
        summary="Get Enrolled Courses",
        description="Get courses the current user is enrolled in",
    )
    async def get_enrolled_subjects(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.get_enrolled(request)

    @router.get(
        "/enrolled/{subject_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[SubjectResponseDto],
        status_code=200,
        summary="Get Enrolled Course",
        description="Get a single enrolled course for the current user",
    )
    async def get_enrolled_one_subject(
        subject_id: int,
        request: Request,
        controller: ISubjectController = Depends(_get_controller),
    ):
        return await controller.get_enrolled_one(request, id=subject_id)

    @router.post(
        "/register",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_validate("subject_id")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Register Course",
        description="Register the current user for a course",
    )
    async def register_subject(
        data: UserSubjectLinkActionDto,
        request: Request,
        controller: ISubjectController = Depends(_get_controller),
    ):
        return await controller.register(request, data=data)

    @router.post(
        "/unregister",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_validate("subject_id")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Unregister Course",
        description="Unregister the current user from a course",
    )
    async def unregister_subject(
        data: UserSubjectLinkActionDto,
        request: Request,
        controller: ISubjectController = Depends(_get_controller),
    ):
        return await controller.unregister(request, data=data)

    return router


def create_subject_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/courses", tags=["Admin Courses"], route_class=CustomRoute
    )

    def _get_controller() -> ISubjectController:
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

    async def _is_ready(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
    ):
        return await auth_middleware.is_ready(request)

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
        "/{subject_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Courses")),
            Depends(_is_ready),
        ],
        response_model=BaseResponseDto[SubjectResponseDto],
        status_code=200,
        summary="Find Course",
        description="Get a course by ID",
    )
    async def find_one_subject(
        subject_id: int,
        request: Request,
        controller: ISubjectController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=subject_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Courses")),
            Depends(_is_ready),
        ],
        response_model=BaseResponseDto[list[SubjectResponseDto]],
        status_code=200,
        summary="Find Courses",
        description="Get all courses",
    )
    async def find_subjects(
        request: Request,
        query: QueryModel[SubjectSearchDto] = Depends(
            Parser.parse_query(QueryModel[SubjectSearchDto])
        ),
        controller: ISubjectController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Courses")),
            Depends(_is_ready),
            Depends(
                _validate(
                    "name",
                    "code",
                    "faculty_id",
                    "department_id",
                    "year_id",
                )
            ),
        ],
        response_model=BaseResponseDto[SubjectResponseDto],
        status_code=201,
        summary="Add Course",
        description="Add a new course",
    )
    async def create_subject(
        data: SubjectCreateDto,
        request: Request,
        controller: ISubjectController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{subject_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Courses")),
            Depends(_is_ready),
            Depends(
                _validate("name", "code", "faculty_id", "department_id", "year_id")
            ),
        ],
        response_model=BaseResponseDto[SubjectResponseDto],
        status_code=200,
        summary="Update Course",
        description="Update an existing course",
    )
    async def update_subject(
        subject_id: int,
        data: SubjectUpdateDto,
        request: Request,
        controller: ISubjectController = Depends(_get_controller),
    ):
        return await controller.update(request, id=subject_id, data=data)

    @router.delete(
        "/{subject_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Courses")),
            Depends(_is_ready),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Delete Course",
        description="Delete an existing course",
    )
    async def delete_subject(
        subject_id: int,
        request: Request,
        controller: ISubjectController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=subject_id)

    return router
