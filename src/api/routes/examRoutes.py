from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iExamController import IExamController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.examDtos import ExamResponseDto


def create_exam_user_router(
    controller_provider,
    auth_middleware_provider,
    validation_middleware_provider,
):
    router = APIRouter(prefix="/exams", tags=["User Exams"], route_class=CustomRoute)

    def _get_controller() -> IExamController:
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

    async def _has_registered_subjects(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
    ):
        return await auth_middleware.has_registered_subjects(request)

    @router.get(
        "/{exam_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[ExamResponseDto],
        status_code=200,
        summary="Find Exam",
        description="Find a specific exam by its ID if enrolled in the subject",
    )
    async def find_one(
        request: Request, controller: IExamController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[ExamResponseDto]],
        status_code=200,
        summary="Find Exams",
        description="Find all exams for the currently logged-in user based on enrolled subjects",
    )
    async def find(
        request: Request, controller: IExamController = Depends(_get_controller)
    ):
        return await controller.find(request)

    return router


def create_exam_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/exams", tags=["Admin Exams"], route_class=CustomRoute)

    def _get_controller() -> IExamController:
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

    async def _has_registered_subjects(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
    ):
        return await auth_middleware.has_registered_subjects(request)

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
        "/{exam_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Exams")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[ExamResponseDto],
        status_code=200,
        summary="Find Exam",
        description="Find an exam by its ID (Admin View)",
    )
    async def find_one(
        request: Request, controller: IExamController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Exams")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[ExamResponseDto]],
        status_code=200,
        summary="Find Exams",
        description="Find exams based on query parameters (Admin View)",
    )
    async def find(
        request: Request, controller: IExamController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Exams")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "deadline", "subject_id")),
        ],
        response_model=BaseResponseDto[ExamResponseDto],
        status_code=201,
        summary="Create Exam",
        description="Create a new exam for a specific subject",
    )
    async def create(
        request: Request, controller: IExamController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/{exam_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Exams")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "deadline", "subject_id")),
        ],
        response_model=BaseResponseDto[ExamResponseDto],
        status_code=200,
        summary="Update Exam",
        description="Update an existing exam by its ID",
    )
    async def update(
        request: Request, controller: IExamController = Depends(_get_controller)
    ):
        return await controller.update(request)

    @router.delete(
        "/{exam_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Exams")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Exam",
        description="Delete a exam by its ID",
    )
    async def delete(
        request: Request, controller: IExamController = Depends(_get_controller)
    ):
        return await controller.delete(request)

    return router
