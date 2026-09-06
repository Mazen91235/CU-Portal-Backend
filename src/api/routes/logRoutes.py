from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute, set_timeout
from core.iControllers.iLogController import ILogController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.logDtos import (
    LogResponseDto,
    LogSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_log_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/logs", tags=["Admin Logs"], route_class=CustomRoute)

    def _get_controller() -> ILogController:
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
        "/count",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Logs")),
        ],
        response_model=BaseResponseDto[int],
        status_code=200,
        summary="Get Logs Count",
        description="Get the total count of logs based on optional filter criteria",
    )
    async def count_logs(
        request: Request,
        query: QueryModel[LogSearchDto] = Depends(
            Parser.parse_query(QueryModel[LogSearchDto])
        ),
        controller: ILogController = Depends(_get_controller),
    ):
        return await controller.count(request, query=query)

    @router.get(
        "/actions",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Logs")),
        ],
        response_model=BaseResponseDto[list[str]],
        status_code=200,
        summary="Get Log Actions",
        description="Get all available log actions",
    )
    async def get_log_actions(
        request: Request,
        controller: ILogController = Depends(_get_controller),
    ):
        return await controller.get_log_actions(request)

    @router.get(
        "/entities",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Logs")),
        ],
        response_model=BaseResponseDto[list[str]],
        status_code=200,
        summary="Get Log Entities",
        description="Get all available log entities",
    )
    async def get_log_entities(
        request: Request,
        controller: ILogController = Depends(_get_controller),
    ):
        return await controller.get_log_entities(request)

    @router.get(
        "/{log_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Logs")),
        ],
        response_model=BaseResponseDto[LogResponseDto],
        status_code=200,
        summary="Find Log",
        description="Get a single log by its ID",
    )
    async def find_one_log(
        log_id: int,
        request: Request,
        controller: ILogController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=log_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Logs")),
        ],
        response_model=BaseResponseDto[list[LogResponseDto]],
        status_code=200,
        summary="Find Logs",
        description="Get all logs matching optional filter criteria",
    )
    async def find_logs(
        request: Request,
        query: QueryModel[LogSearchDto] = Depends(
            Parser.parse_query(QueryModel[LogSearchDto])
        ),
        controller: ILogController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.delete(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Logs")),
            Depends(set_timeout(60)),
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Logs",
        description="Delete logs based on optional filter criteria",
    )
    async def delete_logs(
        logs_count: int,
        request: Request,
        controller: ILogController = Depends(_get_controller),
    ):
        return await controller.delete(request, logs_count=logs_count)

    return router
