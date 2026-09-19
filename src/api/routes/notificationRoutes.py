from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute, set_timeout, allow_inactive
from core.iControllers.iNotificationController import INotificationController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.notificationDtos import (
    NotificationCreateDto,
    NotificationResponseDto,
    NotificationMarkManyAsSeenDto,
)
from core.dtos.userNotificationDtos import UserNotificationSearchDto
from core.dtos.baseDtos import BaseResponseDto
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_notification_public_router(
    controller_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/notifications", tags=["Public Notifications"], route_class=CustomRoute
    )

    def _get_controller() -> INotificationController:
        return controller_provider()

    def _get_validation_middleware() -> IValidationMiddleware:
        return validation_middleware_provider()

    def _validate(*keys):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(
                _get_validation_middleware
            ),
        ):
            return await validation_middleware.validate(request, *keys)

        return validate_request

    async def _validate_api_key(
        request: Request,
        validation_middleware: IValidationMiddleware = Depends(
            _get_validation_middleware
        ),
    ):
        return await validation_middleware.validate_api_key(request)

    @router.post(
        "/",
        dependencies=[
            Depends(_validate_api_key),
            Depends(_validate("notification_type", "parent_id", "content")),
        ],
        response_model=BaseResponseDto,
        summary="Create Notification (Background)",
        description="Creates a new notification in the background.",
    )
    async def create_notification(
        data: NotificationCreateDto,
        request: Request,
        controller: INotificationController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.post(
        "/reminders",
        dependencies=[
            Depends(_validate_api_key),
            Depends(set_timeout(3600)),
        ],  # Set a timeout of 1 hour for the send reminders operation
        response_model=BaseResponseDto,
        summary="Send Reminders (Background)",
        description="Sends reminders for tasks, exams, and events in the background.",
    )
    async def send_reminders(
        request: Request,
        controller: INotificationController = Depends(_get_controller),
    ):
        return await controller.send_reminders(request)

    return router


def create_notification_user_router(controller_provider, auth_middleware_provider):
    router = APIRouter(
        prefix="/notifications", tags=["User Notifications"], route_class=CustomRoute
    )

    def _get_controller() -> INotificationController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

    async def _is_logged_in(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
        refresh_token: str | None = Depends(cookie_scheme),
    ):
        return await auth_middleware.is_logged_in(request, refresh_token)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(allow_inactive())],
        response_model=BaseResponseDto[list[NotificationResponseDto]],
        summary="Get Notifications (User)",
        description="Retrieves a paginated list of notifications for the logged-in user.",
    )
    async def find_notifications(
        request: Request,
        query: QueryModel[UserNotificationSearchDto] = Depends(
            Parser.parse_query(QueryModel[UserNotificationSearchDto])
        ),
        controller: INotificationController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.patch(
        "/seen",
        dependencies=[Depends(_is_logged_in), Depends(allow_inactive())],
        response_model=BaseResponseDto,
        summary="Mark Notifications as Seen",
        description="Marks multiple notifications as seen for the logged-in user.",
    )
    async def mark_notifications_as_seen(
        data: NotificationMarkManyAsSeenDto,
        request: Request,
        controller: INotificationController = Depends(_get_controller),
    ):
        return await controller.mark_notifications_as_seen(request, data=data)

    return router
