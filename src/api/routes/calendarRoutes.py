from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iCalendarController import ICalendarController
from core.iControllers.iFacultyController import IFacultyController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.calendarDtos import (
    CalendarResponseDto,
)
from core.utils.cookieHandler import cookie_scheme


def create_calendar_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/calendar", tags=["User Calendar"], route_class=CustomRoute
    )

    def _get_controller() -> ICalendarController:
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
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[CalendarResponseDto],
        status_code=200,
        summary="Find Calendar Events",
        description="Get calendar events for the logged-in user",
    )
    async def get_calendar_events(
        request: Request,
        date_from: str,
        date_to: str,
        controller: ICalendarController = Depends(_get_controller),
    ):
        return await controller.get_calendar_events(request, date_from, date_to)

    return router
