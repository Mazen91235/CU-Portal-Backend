from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iEventOrganizerController import IEventOrganizerController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.eventOrganizerDtos import (
    EventOrganizerCreateDto,
    EventOrganizerResponseDto,
    EventOrganizerUpdateDto,
    EventOrganizerSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_event_organizer_user_router(controller_provider, auth_middleware_provider):
    router = APIRouter(prefix="/event-organizers", tags=["User Event Organizers"], route_class=CustomRoute)

    def _get_controller() -> IEventOrganizerController:
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
        "/{event_organizer_id}",
        dependencies=[
            Depends(_is_logged_in),
        ],
        response_model=BaseResponseDto[EventOrganizerResponseDto],
        status_code=200,
        summary="Find Event Organizer",
        description="Find a specific event organizer by its ID",
    )
    async def find_one_event_organizer(
        event_organizer_id: int,
        request: Request,
        controller: IEventOrganizerController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=event_organizer_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
        ],
        response_model=BaseResponseDto[list[EventOrganizerResponseDto]],
        status_code=200,
        summary="Find Event Organizers",
        description="Find all event organizers for the currently logged in user",
    )
    async def find_event_organizers(
        request: Request,
        query: QueryModel[EventOrganizerSearchDto] = Depends(
            Parser.parse_query(QueryModel[EventOrganizerSearchDto])
        ),
        controller: IEventOrganizerController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    return router


def create_event_organizer_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/event-organizers", tags=["Admin Event Organizers"], route_class=CustomRoute)

    def _get_controller() -> IEventOrganizerController:
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
        "/{event_organizer_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View EventOrganizers")),
        ],
        response_model=BaseResponseDto[EventOrganizerResponseDto],
        status_code=200,
        summary="Find Event Organizer",
        description="Find an event organizer by its ID (Admin View)",
    )
    async def find_one_event_organizer(
        event_organizer_id: int,
        request: Request,
        controller: IEventOrganizerController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=event_organizer_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View EventOrganizers")),
        ],
        response_model=BaseResponseDto[list[EventOrganizerResponseDto]],
        status_code=200,
        summary="Find Event Organizers",
        description="Find event organizers based on query parameters (Admin View)",
    )
    async def find_event_organizers(
        request: Request,
        query: QueryModel[EventOrganizerSearchDto] = Depends(
            Parser.parse_query(QueryModel[EventOrganizerSearchDto])
        ),
        controller: IEventOrganizerController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add EventOrganizers")),
            Depends(_validate("name", "details")),
        ],
        response_model=BaseResponseDto[EventOrganizerResponseDto],
        status_code=201,
        summary="Create Event Organizer",
        description="Create a new event organizer",
    )
    async def create_event_organizer(
        data: EventOrganizerCreateDto,
        request: Request,
        controller: IEventOrganizerController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{event_organizer_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit EventOrganizers")),
            Depends(_validate("name", "details")),
        ],
        response_model=BaseResponseDto[EventOrganizerResponseDto],
        status_code=200,
        summary="Update Event Organizer",
        description="Update an existing event organizer by its ID",
    )
    async def update_event_organizer(
        event_organizer_id: int,
        data: EventOrganizerUpdateDto,
        request: Request,
        controller: IEventOrganizerController = Depends(_get_controller),
    ):
        return await controller.update(request, id=event_organizer_id, data=data)

    @router.delete(
        "/{event_organizer_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete EventOrganizers")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Delete Event Organizer",
        description="Delete an event organizer by its ID",
    )
    async def delete_event_organizer(
        event_organizer_id: int,
        request: Request,
        controller: IEventOrganizerController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=event_organizer_id)

    return router
