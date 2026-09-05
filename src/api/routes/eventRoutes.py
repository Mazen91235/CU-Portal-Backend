from fastapi import APIRouter, Request, Depends
from core.iControllers.iEventController import IEventController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.eventDtos import EventResponseDto


def create_event_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/events", tags=["Events"])

    def _get_controller() -> IEventController:
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
        request: Request, auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware)
    ):
        return await auth_middleware.is_ready(request)

    def _validate(*keys):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(_get_validation_middleware),
        ):
            return await validation_middleware.validate(request, *keys)
        return validate_request
    
    @router.get(
            "/{event_id}", dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
            response_model=BaseResponseDto[EventResponseDto], status_code=200,
            summary="Find Event", description="Get an event by ID",
        )
    async def find_one(request: Request, controller: IEventController = Depends(_get_controller)):
        return await controller.find_one(request)
    
    @router.get(
            "/", dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
            response_model=BaseResponseDto[list[EventResponseDto]], status_code=200,
            summary="Find Events", description="Get events available to the current user",
        )
    async def find(request: Request, controller: IEventController = Depends(_get_controller)):
        return await controller.find(request)
        
    @router.post(
        "/register",
        dependencies=[Depends(_is_logged_in), Depends(_validate("event_id")), Depends(_is_ready)],
        response_model=BaseResponseDto[bool], status_code=200,
        summary="Register For Event", description="Register the current user as an attendee of an event",
    )
    async def register(request: Request, controller: IEventController = Depends(_get_controller)):
        return await controller.register(request)

    @router.post(
        "/unregister",
        dependencies=[Depends(_is_logged_in), Depends(_validate("event_id")), Depends(_is_ready)],
        response_model=BaseResponseDto[bool], status_code=200,
        summary="Unregister From Event", description="Unregister the current user as an attendee of an event",
    )
    async def unregister(request: Request, controller: IEventController = Depends(_get_controller)):
        return await controller.unregister(request)

    return router


def create_event_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/events", tags=["Events"])

    def _get_controller() -> IEventController:
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
            Depends(_is_authorized("View Events")),
        ],
        response_model=BaseResponseDto[EventResponseDto],
        status_code=200,
        summary="Get Event",
        description="Get a specific event by its ID",
    )
    async def find_one(
        request: Request, controller: IEventController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Events")),
        ],
        response_model=BaseResponseDto[EventResponseDto],
        status_code=200,
        summary="Get Events",
        description="Get a list of all events",
    )
    async def find(
        request: Request, controller: IEventController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Events")),
            Depends(_validate("title", "start_date", "url","price","location_type","location","event_organizer_id")),
        ],
        response_model=BaseResponseDto[EventResponseDto],
        status_code=201,
        summary="Create Event",
        description="Create a new event",
    )
    async def create(
        request: Request, controller: IEventController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/{event_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Events")),
            Depends(_validate("title", "start_date", "url","price","location_type","location",)),
        ],
        response_model=BaseResponseDto[EventResponseDto],
        status_code=200,
        summary="Update Event",
        description="Update an existing event",
    )
    async def update(
        request: Request, controller: IEventController = Depends(_get_controller)
    ):
        return await controller.update(request)

    @router.delete(
        "/{event_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Events")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Delete Events",
        description="Delete an event by its ID",
    )
    async def delete(
        request: Request, controller: IEventController = Depends(_get_controller)
    ):
        return await controller.delete(request)

    

    return router
