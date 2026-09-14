from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iReleaseController import IReleaseController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.releaseDtos import (
    ReleaseCreateDto,
    ReleaseResponseDto,
    ReleaseUpdateDto,
    ReleaseSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_release_user_router(controller_provider, auth_middleware_provider):
    router = APIRouter(
        prefix="/releases", tags=["User Releases"], route_class=CustomRoute
    )

    def _get_controller() -> IReleaseController:
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
        "/versions",
        dependencies=[
            Depends(_is_logged_in),
        ],
        response_model=BaseResponseDto[list[int]],
        status_code=200,
        summary="Find Release Versions",
        description="Get all release versions in the system",
    )
    async def find_release_versions(
        request: Request,
        controller: IReleaseController = Depends(_get_controller),
    ):
        return await controller.find_versions(request)

    @router.get(
        "/{release_id}",
        dependencies=[
            Depends(_is_logged_in),
        ],
        response_model=BaseResponseDto[ReleaseResponseDto],
        status_code=200,
        summary="Find Release",
        description="Get a single release by its ID",
    )
    async def find_one_release(
        release_id: int,
        request: Request,
        controller: IReleaseController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=release_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
        ],
        response_model=BaseResponseDto[list[ReleaseResponseDto]],
        status_code=200,
        summary="Find Releases",
        description="Get all releases matching optional filter criteria",
    )
    async def find_releases(
        request: Request,
        query: QueryModel[ReleaseSearchDto] = Depends(
            Parser.parse_query(QueryModel[ReleaseSearchDto])
        ),
        controller: IReleaseController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    return router


def create_release_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/releases", tags=["Admin Releases"], route_class=CustomRoute
    )

    def _get_controller() -> IReleaseController:
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
        "/versions",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Releases")),
        ],
        response_model=BaseResponseDto[list[int]],
        status_code=200,
        summary="Find Release Versions",
        description="Get all release versions in the system",
    )
    async def find_release_versions(
        request: Request,
        controller: IReleaseController = Depends(_get_controller),
    ):
        return await controller.find_versions(request)

    @router.get(
        "/{release_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Releases")),
        ],
        response_model=BaseResponseDto[ReleaseResponseDto],
        status_code=200,
        summary="Find Release",
        description="Get a single release by its ID",
    )
    async def find_one_release(
        release_id: int,
        request: Request,
        controller: IReleaseController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=release_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Releases")),
        ],
        response_model=BaseResponseDto[list[ReleaseResponseDto]],
        status_code=200,
        summary="Find Releases",
        description="Get all releases matching optional filter criteria",
    )
    async def find_releases(
        request: Request,
        query: QueryModel[ReleaseSearchDto] = Depends(
            Parser.parse_query(QueryModel[ReleaseSearchDto])
        ),
        controller: IReleaseController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Releases")),
            Depends(_validate("release_number", "title", "date", "release_items")),
        ],
        response_model=BaseResponseDto[ReleaseResponseDto],
        status_code=201,
        summary="Create Release",
        description="Create a new release",
    )
    async def create_release(
        data: ReleaseCreateDto,
        request: Request,
        controller: IReleaseController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{release_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Releases")),
            Depends(_validate("release_number", "title", "date", "release_items")),
        ],
        response_model=BaseResponseDto[ReleaseResponseDto],
        status_code=200,
        summary="Update Release",
        description="Update an existing release",
    )
    async def update_release(
        release_id: int,
        data: ReleaseUpdateDto,
        request: Request,
        controller: IReleaseController = Depends(_get_controller),
    ):
        return await controller.update(request, id=release_id, data=data)

    @router.delete(
        "/{release_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Releases")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Delete Release",
        description="Delete an existing release",
    )
    async def delete_release(
        release_id: int,
        request: Request,
        controller: IReleaseController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=release_id)

    return router
