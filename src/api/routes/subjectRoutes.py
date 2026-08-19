from fastapi import APIRouter, Request, Depends
from core.iControllers.iSubjectController import ISubjectController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.subjectDtos import SubjectResponseDto


def create_subject_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/courses", tags=["Courses"])

    def _get_controller() -> ISubjectController:
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
    async def get_available(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.get_available(request)

    @router.get(
        "/enrolled",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[list[SubjectResponseDto]],
        status_code=200,
        summary="Get Enrolled Courses",
        description="Get courses the current user is enrolled in",
    )
    async def get_enrolled(
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
    async def get_enrolled_one(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.get_enrolled_one(request)

    @router.post(
        "/register",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_validate("subject_id")),
            Depends(_is_ready),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Register Course",
        description="Register the current user for a course",
    )
    async def register(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.register(request)

    @router.post(
        "/unregister",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_validate("subject_id")),
            Depends(_is_ready),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Unregister Course",
        description="Unregister the current user from a course",
    )
    async def unregister(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.unregister(request)

    return router


def create_subject_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/courses", tags=["Courses"])

    def _get_controller() -> ISubjectController:
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
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Courses"))],
        response_model=BaseResponseDto[SubjectResponseDto],
        status_code=200,
        summary="Find Course",
        description="Get a course by ID",
    )
    async def find_one(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Courses"))],
        response_model=BaseResponseDto[list[SubjectResponseDto]],
        status_code=200,
        summary="Find Courses",
        description="Get all courses",
    )
    async def find(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Courses")),
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
    async def create(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/{subject_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Courses")),
            Depends(
                _validate("name", "code", "faculty_id", "department_id", "year_id")
            ),
        ],
        response_model=BaseResponseDto[SubjectResponseDto],
        status_code=200,
        summary="Update Course",
        description="Update an existing course",
    )
    async def update(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.update(request)

    @router.delete(
        "/{subject_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Courses")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Delete Course",
        description="Delete an existing course",
    )
    async def delete(
        request: Request, controller: ISubjectController = Depends(_get_controller)
    ):
        return await controller.delete(request)

    return router
