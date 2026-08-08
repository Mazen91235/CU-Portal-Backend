from fastapi import APIRouter, Request, Depends
from core.iControllers.iExamController import IExamController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.iMiddlewares.iRequestLimitMiddleware import IRequestLimitMiddleware
from core.dtos.baseDtos import BaseResponseDto

# ---------------------------------------------------------
# Admin Router
# ---------------------------------------------------------
def create_exam_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider, rate_limit_provider
):
    router = APIRouter(prefix="/exams", tags=["Admin Exams"])

    def _get_controller() -> IExamController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()
        
    def _get_rate_limit_middleware() -> IRequestLimitMiddleware:
        return rate_limit_provider()

    async def _is_logged_in(request: Request, auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware)):
        return await auth_middleware.is_logged_in(request)

    def _is_authorized(*permissions):
        async def authorized_request(request: Request, auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware)):
            return await auth_middleware.is_authorized(request, *permissions)
        return authorized_request
        
    async def _rate_limit(request: Request, rate_middleware: IRequestLimitMiddleware = Depends(_get_rate_limit_middleware)):
        return await rate_middleware.throttle(request)

    @router.post(
        "",
        dependencies=[Depends(_is_logged_in), Depends(_rate_limit), Depends(_is_authorized("Add Exams"))],
        response_model=BaseResponseDto,
        summary="Create Exam",
    )
    async def create_exam(request: Request, controller: IExamController = Depends(_get_controller)):
        return await controller.create_exam(request)

    @router.patch(
        "/{exam_id}",
        dependencies=[Depends(_is_logged_in), Depends(_rate_limit), Depends(_is_authorized("Edit Exams"))],
        response_model=BaseResponseDto,
        summary="Update Exam",
    )
    async def update_exam(exam_id: int, request: Request, controller: IExamController = Depends(_get_controller)):
        return await controller.update_exam(request, exam_id)

    @router.delete(
        "/{exam_id}",
        dependencies=[Depends(_is_logged_in), Depends(_rate_limit), Depends(_is_authorized("Delete Exams"))],
        response_model=BaseResponseDto,
        summary="Delete Exam",
    )
    async def delete_exam(exam_id: int, request: Request, controller: IExamController = Depends(_get_controller)):
        return await controller.delete_exam(request, exam_id)

    @router.get(
        "",
        dependencies=[Depends(_is_logged_in), Depends(_rate_limit), Depends(_is_authorized("View Exams"))],
        response_model=BaseResponseDto,
        summary="Get All Exams (Admin)",
    )
    async def get_exams_admin(request: Request, controller: IExamController = Depends(_get_controller)):
        return await controller.get_exams_admin(request)

    @router.get(
        "/{exam_id}",
        dependencies=[Depends(_is_logged_in), Depends(_rate_limit), Depends(_is_authorized("View Exams"))],
        response_model=BaseResponseDto,
        summary="Get Exam by ID (Admin)",
    )
    async def get_exam_admin(exam_id: int, request: Request, controller: IExamController = Depends(_get_controller)):
        return await controller.get_exam_admin(request, exam_id)

    return router


# ---------------------------------------------------------
# User Router
# ---------------------------------------------------------
def create_exam_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider, rate_limit_provider
):
    router = APIRouter(prefix="/exams", tags=["User Exams"])

    def _get_controller() -> IExamController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()
        
    def _get_rate_limit_middleware() -> IRequestLimitMiddleware:
        return rate_limit_provider()

    async def _is_logged_in(request: Request, auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware)):
        return await auth_middleware.is_logged_in(request)
        
    async def _rate_limit(request: Request, rate_middleware: IRequestLimitMiddleware = Depends(_get_rate_limit_middleware)):
        return await rate_middleware.throttle(request)

    @router.get(
        "",
        dependencies=[Depends(_is_logged_in), Depends(_rate_limit)],
        response_model=BaseResponseDto,
        summary="Get Enrolled Exams (User)",
    )
    async def get_exams_user(request: Request, controller: IExamController = Depends(_get_controller)):
        return await controller.get_exams_user(request)

    @router.get(
        "/{exam_id}",
        dependencies=[Depends(_is_logged_in), Depends(_rate_limit)],
        response_model=BaseResponseDto,
        summary="Get Exam Detail (User)",
    )
    async def get_exam_user(exam_id: int, request: Request, controller: IExamController = Depends(_get_controller)):
        return await controller.get_exam_user(request, exam_id)

    return router