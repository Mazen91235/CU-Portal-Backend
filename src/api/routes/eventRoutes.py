from fastapi import APIRouter, Request, Depends
from core.iControllers.iEventController import IEventController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.eventDtos import (
    EventCreateDto,
    EventResponseDto,
    EventUpdateDto,
    EventSearchDto,
)
from core.dtos.userEventDtos import UserEventActionDto
from core.dtos.baseDtos import BaseResponseDto
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_event_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/events", tags=["User Events"])

    def _get_controller() -> IEventController:
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
        "/{event_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[EventResponseDto],
        status_code=200,
        summary="Find Event",
        description="Get an event by ID",
    )
    async def find_one_event(
        event_id: int,
        request: Request,
        controller: IEventController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=event_id)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[list[EventResponseDto]],
        status_code=200,
        summary="Find Events",
        description="Get events available to the current user",
    )
    async def find_events(
        request: Request,
        query: QueryModel[EventSearchDto] = Depends(
            Parser.parse_query(QueryModel[EventSearchDto])
        ),
        controller: IEventController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/register",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_validate("event_id")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Register For Event",
        description="Register the current user as an attendee of an event",
    )
    async def register_event(
        data: UserEventActionDto,
        request: Request,
        controller: IEventController = Depends(_get_controller),
    ):
        return await controller.register(request, data=data)

    @router.post(
        "/unregister",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_validate("event_id")),
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Unregister From Event",
        description="Unregister the current user as an attendee of an event",
    )
    async def unregister_event(
        data: UserEventActionDto,
        request: Request,
        controller: IEventController = Depends(_get_controller),
    ):
        return await controller.unregister(request, data=data)

    return router


def create_event_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/events", tags=["Admin Events"])

    def _get_controller() -> IEventController:
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
        "/{event_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_is_authorized("View Events")),
        ],
        response_model=BaseResponseDto[EventResponseDto],
        status_code=200,
        summary="Get Event",
        description="Get a specific event by its ID",
    )
    async def find_one_event(
        event_id: int,
        request: Request,
        controller: IEventController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=event_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_is_authorized("View Events")),
        ],
        response_model=BaseResponseDto[EventResponseDto],
        status_code=200,
        summary="Get Events",
        description="Get a list of all events",
    )
    async def find_events(
        request: Request,
        query: QueryModel[EventSearchDto] = Depends(
            Parser.parse_query(QueryModel[EventSearchDto])
        ),
        controller: IEventController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_is_authorized("Add Events")),
            Depends(
                _validate(
                    "title",
                    "start_date",
                    "price",
                    "location_type",
                    "location",
                    "event_organizer_id",
                    "details",
                )
            ),
        ],
        response_model=BaseResponseDto[EventResponseDto],
        status_code=201,
        summary="Create Event",
        description="Create a new event",
    )
    async def create_event(
        data: EventCreateDto,
        request: Request,
        controller: IEventController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{event_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_is_authorized("Edit Events")),
            Depends(
                _validate(
                    "title",
                    "start_date",
                    "price",
                    "location_type",
                    "location",
                    "event_organizer_id",
                    "details",
                )
            ),
        ],
        response_model=BaseResponseDto[EventResponseDto],
        status_code=200,
        summary="Update Event",
        description="Update an existing event",
    )
    async def update_event(
        event_id: int,
        data: EventUpdateDto,
        request: Request,
        controller: IEventController = Depends(_get_controller),
    ):
        return await controller.update(request, id=event_id, data=data)

    @router.delete(
        "/{event_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_is_authorized("Delete Events")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Delete Events",
        description="Delete an event by its ID",
    )
    async def delete_event(
        event_id: int,
        request: Request,
        controller: IEventController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=event_id)

    return router
