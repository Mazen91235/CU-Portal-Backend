from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iExamController import IExamController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.examDtos import (
    ExamCreateDto,
    ExamResponseDto,
    ExamUpdateDto,
    ExamSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


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
        refresh_token: str | None = Depends(cookie_scheme),
    ):
        return await auth_middleware.is_logged_in(request, refresh_token)

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
    async def find_one_exam(
        exam_id: int,
        request: Request,
        controller: IExamController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=exam_id)

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
    async def find_exams(
        request: Request,
        query: QueryModel[ExamSearchDto] = Depends(
            Parser.parse_query(QueryModel[ExamSearchDto])
        ),
        controller: IExamController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

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
        refresh_token: str | None = Depends(cookie_scheme),
    ):
        return await auth_middleware.is_logged_in(request, refresh_token)

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

    def _validate_details_numbers(*keys):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(
                _get_validation_middleware
            ),
        ):
            return await validation_middleware.validate_details_numbers(request, *keys)

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
    async def find_one_exam(
        exam_id: int,
        request: Request,
        controller: IExamController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=exam_id)

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
    async def find_exams(
        request: Request,
        query: QueryModel[ExamSearchDto] = Depends(
            Parser.parse_query(QueryModel[ExamSearchDto])
        ),
        controller: IExamController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Exams")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "deadline", "subject_id")),
            Depends(_validate_details_numbers("duration")),
        ],
        response_model=BaseResponseDto[ExamResponseDto],
        status_code=201,
        summary="Create Exam",
        description="Create a new exam for a specific subject",
    )
    async def create_exam(
        data: ExamCreateDto,
        request: Request,
        controller: IExamController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{exam_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Exams")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "deadline", "subject_id")),
            Depends(_validate_details_numbers("duration"))
        ],
        response_model=BaseResponseDto[ExamResponseDto],
        status_code=200,
        summary="Update Exam",
        description="Update an existing exam by its ID",
    )
    async def update_exam(
        exam_id: int,
        data: ExamUpdateDto,
        request: Request,
        controller: IExamController = Depends(_get_controller),
    ):
        return await controller.update(request, id=exam_id, data=data)

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
    async def delete_exam(
        exam_id: int,
        request: Request,
        controller: IExamController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=exam_id)

    return router
