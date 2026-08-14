from fastapi import APIRouter, Request, Depends
from customRoute import CustomRoute
from core.iControllers.iNotificationController import INotificationController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.notificationDtos import NotificationResponseDto
from core.dtos.baseDtos import BaseResponseDto


def create_notification_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/notifications", tags=["User Notifications"], route_class=CustomRoute
    )

    def _get_controller() -> INotificationController:
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
        dependencies=[Depends(_is_logged_in)],
        response_model=BaseResponseDto[list[NotificationResponseDto]],
        summary="Get Notifications (User)",
        description="Retrieves a paginated list of notifications for the logged-in user.",
    )
    async def find(
        request: Request, controller: INotificationController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.patch(
        "/{notification_id}",
        dependencies=[Depends(_is_logged_in)],
        response_model=BaseResponseDto[bool],
        summary="Mark Notification as Seen",
        description="Marks a specific notification as seen for the logged-in user.",
    )
    async def mark_notification_as_seen(
        request: Request,
        controller: INotificationController = Depends(_get_controller),
    ):
        return await controller.mark_notification_as_seen(request)

    return router
