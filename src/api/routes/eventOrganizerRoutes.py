from fastapi import APIRouter, Request, Depends
from core.iControllers.iEventOrganizerController import IEventOrganizerController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.eventOrganizerDtos import EventOrganizerResponseDto


def create_event_organizer_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/event-organizers", tags=["User Event Organizers"])

    def _get_controller() -> IEventOrganizerController:
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
        "/{event_organizer_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[EventOrganizerResponseDto],
        status_code=200,
        summary="Find Event Organizer",
        description="Find a specific event organizer by its ID",
    )
    async def find_one(
        request: Request, controller: IEventOrganizerController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[EventOrganizerResponseDto]],
        status_code=200,
        summary="Find Event Organizers",
        description="Find all event organizers for the currently logged in user",
    )
    async def find(
        request: Request, controller: IEventOrganizerController = Depends(_get_controller)
    ):
        return await controller.find(request)

    return router


def create_event_organizer_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/event-organizers", tags=["Admin Event Organizers"])

    def _get_controller() -> IEventOrganizerController:
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
        "/{event_organizer_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Event Organizers")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[EventOrganizerResponseDto],
        status_code=200,
        summary="Find Event Organizer",
        description="Find an event organizer by its ID (Admin View)",
    )
    async def find_one(
        request: Request, controller: IEventOrganizerController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Event Organizers")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[EventOrganizerResponseDto]],
        status_code=200,
        summary="Find Event Organizers",
        description="Find event organizers based on query parameters (Admin View)",
    )
    async def find(
        request: Request, controller: IEventOrganizerController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Event Organizers")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "url")),
        ],
        response_model=BaseResponseDto[EventOrganizerResponseDto],
        status_code=201,
        summary="Create Event Organizer",
        description="Create a new event organizer",
    )
    async def create(
        request: Request, controller: IEventOrganizerController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/{event_organizer_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Event Organizers")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "url")),
        ],
        response_model=BaseResponseDto[EventOrganizerResponseDto],
        status_code=200,
        summary="Update Event Organizer",
        description="Update an existing event organizer by its ID",
    )
    async def update(
        request: Request, controller: IEventOrganizerController = Depends(_get_controller)
    ):
        return await controller.update(request)

    @router.delete(
        "/{event_organizer_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Event Organizers")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Event Organizer",
        description="Delete an event organizer by its ID",
    )
    async def delete(
        request: Request, controller: IEventOrganizerController = Depends(_get_controller)
    ):
        return await controller.delete(request)

    return router