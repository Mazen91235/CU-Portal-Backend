from fastapi import APIRouter, Request, Depends
from core.iControllers.iTaskController import ITaskController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.taskDtos import TaskResponseDto


def create_task_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/tasks", tags=["User Tasks"])

    def _get_controller() -> ITaskController:
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
        "/{task_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects)
        ],
        response_model=BaseResponseDto[TaskResponseDto],
        status_code=200,
        summary="Find Task",
        description="Find a specific task by its ID if enrolled in the subject",
    )
    async def find_one(  # type: ignore
        request: Request, controller: ITaskController = Depends(_get_controller)
    ):
        return await controller.find_one(request)
    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects)
        ],
        response_model=BaseResponseDto[list[TaskResponseDto]],
        status_code=200,
        summary="Find Tasks",
        description="Find all tasks for the currently logged-in user based on enrolled subjects",
    )
    async def find(  # type: ignore
        request: Request, controller: ITaskController = Depends(_get_controller)
    ):
        return await controller.find(request)


    return router


def create_task_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/tasks", tags=["Admin Tasks"])

    def _get_controller() -> ITaskController:
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
        "/{task_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects)
        ],
        response_model=BaseResponseDto[TaskResponseDto],
        status_code=200,
        summary="Find Task",
        description="Find a task by its ID (Admin View)",
    )
    async def find_one(  # type: ignore
        request: Request, controller: ITaskController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects)
        ],
        response_model=BaseResponseDto[list[TaskResponseDto]],
        status_code=200,
        summary="Find Tasks",
        description="Find tasks based on query parameters (Admin View)",
    )
    async def find(  # type: ignore
        request: Request, controller: ITaskController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Manage Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "url", "urls", "links", "details", "deadline", "due_date", "subject_id", "department_id", "faculty_id", "year_id"))
        ],
        response_model=BaseResponseDto[TaskResponseDto],
        status_code=201,
        summary="Create Task",
        description="Create a new task for a specific subject",
    )
    async def create(  # type: ignore
        request: Request, controller: ITaskController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/{task_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Manage Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "url", "urls", "links", "details", "deadline", "due_date", "subject_id", "department_id", "faculty_id", "year_id"))
        ],
        response_model=BaseResponseDto[TaskResponseDto],
        status_code=200,
        summary="Update Task",
        description="Update an existing task by its ID",
    )
    async def update(  # type: ignore
        request: Request, controller: ITaskController = Depends(_get_controller)
    ):
        return await controller.update(request)

    @router.delete(
        "/{task_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Manage Tasks")),
            Depends(_is_ready),
            Depends(_has_registered_subjects)
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Task",
        description="Delete a task by its ID",
    )
    async def delete(  # type: ignore
        request: Request, controller: ITaskController = Depends(_get_controller)
    ):
        return await controller.delete(request)

    return router