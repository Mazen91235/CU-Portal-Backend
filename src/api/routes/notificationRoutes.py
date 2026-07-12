from fastapi import APIRouter, Request, Depends
from core.iControllers.iNotificationController import INotificationController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iRequestLimitMiddleware import IRequestLimitMiddleware
from core.dtos.baseDtos import BaseResponseDto

# User Router
def create_notification_router(
    controller_provider, auth_middleware_provider, rate_limit_provider
):
    router = APIRouter(prefix="/notifications", tags=["User Notifications"])

    def _get_controller() -> INotificationController:
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
        summary="Get Notifications (User)",
        description="Retrieves a paginated list of notifications for the logged-in user."
    )
    async def get_notifications_user(request: Request, controller: INotificationController = Depends(_get_controller)):
        return await controller.get_notifications_user(request)

    @router.patch(
        "/{notification_id}",
        dependencies=[Depends(_is_logged_in), Depends(_rate_limit)],
        response_model=BaseResponseDto,
        summary="Mark Notification as Seen",
        description="Marks a specific notification as seen for the logged-in user."
    )
    async def mark_notification_as_seen(notification_id: int, request: Request, controller: INotificationController = Depends(_get_controller)):
        return await controller.mark_notification_as_seen(request, notification_id)

    return router