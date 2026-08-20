from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iTaskController import ITaskController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.taskDtos import (
    TaskCreateDto,
    TaskResponseDto,
    TaskUpdateDto,
    TaskSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.cookieHandler import cookie_scheme


def create_task_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/tasks", tags=["User Tasks"], route_class=CustomRoute)

    def _get_controller() -> ITaskController:
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
        "/{task_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[TaskResponseDto],
        status_code=200,
        summary="Find Task",
        description="Find a specific task by its ID if enrolled in the subject",
    )
    async def find_one_task(
        task_id: int,
        request: Request,
        controller: ITaskController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=task_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[TaskResponseDto]],
        status_code=200,
        summary="Find Tasks",
        description="Find all tasks for the currently logged-in user based on enrolled subjects",
    )
    async def find_tasks(
        query: QueryModel[TaskSearchDto],
        request: Request,
        controller: ITaskController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    return router


def create_task_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/tasks", tags=["Admin Tasks"], route_class=CustomRoute)

    def _get_controller() -> ITaskController:
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

    @router.get(
        "/{task_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[TaskResponseDto],
        status_code=200,
        summary="Find Task",
        description="Find a task by its ID (Admin View)",
    )
    async def find_one_task(
        task_id: int,
        request: Request,
        controller: ITaskController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=task_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[TaskResponseDto]],
        status_code=200,
        summary="Find Tasks",
        description="Find tasks based on query parameters (Admin View)",
    )
    async def find_tasks(
        query: QueryModel[TaskSearchDto],
        request: Request,
        controller: ITaskController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "deadline", "subject_id")),
        ],
        response_model=BaseResponseDto[TaskResponseDto],
        status_code=201,
        summary="Create Task",
        description="Create a new task for a specific subject",
    )
    async def create_task(
        data: TaskCreateDto,
        request: Request,
        controller: ITaskController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{task_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "deadline", "subject_id")),
        ],
        response_model=BaseResponseDto[TaskResponseDto],
        status_code=200,
        summary="Update Task",
        description="Update an existing task by its ID",
    )
    async def update_task(
        task_id: int,
        data: TaskUpdateDto,
        request: Request,
        controller: ITaskController = Depends(_get_controller),
    ):
        return await controller.update(request, id=task_id, data=data)

    @router.delete(
        "/{task_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Task",
        description="Delete a task by its ID",
    )
    async def delete_task(
        task_id: int,
        request: Request,
        controller: ITaskController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=task_id)

    return router
