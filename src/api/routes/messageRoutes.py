from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iMessageController import IMessageController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.messageDtos import MessageCreateDto, MessageResponseDto, MessageSearchDto
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_message_public_router(controller_provider, validation_middleware_provider):
    router = APIRouter(prefix="/messages", tags=["Messages"], route_class=CustomRoute)

    def _get_controller() -> IMessageController:
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

    @router.post(
        "/",
        dependencies=[Depends(_validate("name", "email", "phone", "content"))],
        response_model=BaseResponseDto[MessageResponseDto],
        status_code=201,
        summary="Create Message",
        description="Submit a contact-us message",
    )
    async def create_message(
        data: MessageCreateDto,
        request: Request,
        controller: IMessageController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    return router


def create_message_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/messages", tags=["Messages"], route_class=CustomRoute)

    def _get_controller() -> IMessageController:
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
        "/{message_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Messages"))],
        response_model=BaseResponseDto[MessageResponseDto],
        status_code=200,
        summary="Find Message",
        description="Find a contact-us message by id",
    )
    async def find_one_message(
        message_id: int,
        request: Request,
        controller: IMessageController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=message_id)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Messages"))],
        response_model=BaseResponseDto[list[MessageResponseDto]],
        status_code=200,
        summary="Find Messages",
        description="Find contact-us messages based on query parameters",
    )
    async def find_messages(
        request: Request,
        query: QueryModel[MessageSearchDto] = Depends(
            Parser.parse_query(QueryModel[MessageSearchDto])
        ),
        controller: IMessageController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    return router
