from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iWeekController import IWeekController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.weekDtos import (
    WeekCreateDto,
    WeekResponseDto,
    WeekUpdateDto,
    WeekSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_week_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/weeks", tags=["User Weeks"], route_class=CustomRoute)

    def _get_controller() -> IWeekController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

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

    @router.get(
        "/{week_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[WeekResponseDto],
        status_code=200,
        summary="Find Week",
        description="Find a week by its ID",
    )
    async def find_one_week(
        week_id: int,
        request: Request,
        controller: IWeekController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=week_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[WeekResponseDto]],
        status_code=200,
        summary="Find Weeks",
        description="Find weeks based on query parameters",
    )
    async def find_weeks(
        request: Request,
        query: QueryModel[WeekSearchDto] = Depends(
            Parser.parse_query(QueryModel[WeekSearchDto])
        ),
        controller: IWeekController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    return router


def create_week_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/weeks", tags=["Admin Weeks"], route_class=CustomRoute)

    def _get_controller() -> IWeekController:
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
        "/{week_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Weeks"))],
        response_model=BaseResponseDto[WeekResponseDto],
        status_code=200,
        summary="Find Week",
        description="Find a week by its ID",
    )
    async def find_one_week(
        week_id: int,
        request: Request,
        controller: IWeekController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=week_id)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Weeks"))],
        response_model=BaseResponseDto[list[WeekResponseDto]],
        status_code=200,
        summary="Find Weeks",
        description="Find weeks based on query parameters",
    )
    async def find_weeks(
        request: Request,
        query: QueryModel[WeekSearchDto] = Depends(
            Parser.parse_query(QueryModel[WeekSearchDto])
        ),
        controller: IWeekController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Weeks")),
            Depends(_validate("week_number")),
        ],
        response_model=BaseResponseDto[WeekResponseDto],
        status_code=201,
        summary="Create Week",
        description="Create a new week",
    )
    async def create_week(
        data: WeekCreateDto,
        request: Request,
        controller: IWeekController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{week_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Weeks")),
            Depends(_validate("week_number")),
        ],
        response_model=BaseResponseDto[WeekResponseDto],
        status_code=200,
        summary="Update Week",
        description="Update a week by its ID",
    )
    async def update_week(
        week_id: int,
        data: WeekUpdateDto,
        request: Request,
        controller: IWeekController = Depends(_get_controller),
    ):
        return await controller.update(request, id=week_id, data=data)

    @router.delete(
        "/{week_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("Delete Weeks"))],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Week",
        description="Delete a week by its ID",
    )
    async def delete_week(
        week_id: int,
        request: Request,
        controller: IWeekController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=week_id)

    return router
