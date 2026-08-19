from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iYearController import IYearController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.yearDtos import YearResponseDto


def create_year_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/years", tags=["Years"], route_class=CustomRoute)

    def _get_controller() -> IYearController:
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
        "/{year_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Years"))],
        response_model=BaseResponseDto[YearResponseDto],
        status_code=200,
        summary="Find Year",
        description="Find an academic year by its ID",
    )
    async def find_one(
        request: Request, controller: IYearController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Years"))],
        response_model=BaseResponseDto[list[YearResponseDto]],
        status_code=200,
        summary="Find Years",
        description="Find academic years based on query parameters",
    )
    async def find(
        request: Request, controller: IYearController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Years")),
            Depends(_validate("year")),
        ],
        response_model=BaseResponseDto[YearResponseDto],
        status_code=201,
        summary="Create Year",
        description="Create a new academic year",
    )
    async def create(
        request: Request, controller: IYearController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/{year_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Years")),
            Depends(_validate("year")),
        ],
        response_model=BaseResponseDto[YearResponseDto],
        status_code=200,
        summary="Update Year",
        description="Update an academic year by its ID",
    )
    async def update(
        request: Request, controller: IYearController = Depends(_get_controller)
    ):
        return await controller.update(request)

    @router.delete(
        "/{year_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("Delete Years"))],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Year",
        description="Delete an academic year by its ID",
    )
    async def delete(
        request: Request, controller: IYearController = Depends(_get_controller)
    ):
        return await controller.delete(request)

    return router
