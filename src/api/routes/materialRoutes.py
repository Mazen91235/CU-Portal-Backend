from fastapi import APIRouter, Request, Depends
from core.iControllers.iMaterialController import IMaterialController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.materialDtos import (
    MaterialResponseDto,
    MaterialMinimalResponseDto,
    DriveMaterialPreviewDto,
)


def create_material_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/materials", tags=["Materials"])

    def _get_controller() -> IMaterialController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

    async def _is_logged_in(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
    ):
        return await auth_middleware.is_logged_in(request)

    @router.get(
        "/{material_id}",
        dependencies=[Depends(_is_logged_in)],
        response_model=BaseResponseDto[MaterialResponseDto],
        status_code=200,
        summary="Get Material Detail",
        description="Get the detail of a material for the currently logged in user",
    )
    async def get_detail(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.get_detail(request)

    @router.get(
        "/{material_id}/parents",
        dependencies=[Depends(_is_logged_in)],
        response_model=BaseResponseDto[list[MaterialMinimalResponseDto]],
        status_code=200,
        summary="Get Material Parents",
        description="Get the parent chain of a specific material by its ID",
    )
    async def get_parents(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.get_parents(request)

    return router


def create_material_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/materials", tags=["Materials"])

    def _get_controller() -> IMaterialController:
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

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Materials")),
            Depends(_validate("name", "type", "url", "parent_id", "subject_id")),
        ],
        response_model=BaseResponseDto[MaterialResponseDto],
        status_code=201,
        summary="Create Material",
        description="Create a new material",
    )
    async def create(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/update/{material_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Materials")),
            Depends(_validate("name", "description", "url")),
        ],
        response_model=BaseResponseDto[MaterialResponseDto],
        status_code=200,
        summary="Update Material",
        description="Update an existing material",
    )
    async def update(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.update(request)

    @router.get(
        "/fetch-one-from-drive",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Materials")),
        ],
        response_model=BaseResponseDto[DriveMaterialPreviewDto],
        status_code=200,
        summary="Fetch One Material From Drive",
        description="Fetch a single material's metadata from Google Drive",
    )
    async def fetch_one_material_from_drive(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.fetch_one_material_from_drive(request)

    @router.get(
        "/fetch-from-drive",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Materials")),
        ],
        response_model=BaseResponseDto[MaterialResponseDto],
        status_code=201,
        summary="Fetch Materials From Drive",
        description="Fetch materials from a Google Drive URL and create them",
    )
    async def fetch_materials_from_drive(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.fetch_materials_from_drive(request)

    @router.get(
        "/{material_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Materials")),
        ],
        response_model=BaseResponseDto[MaterialResponseDto],
        status_code=200,
        summary="Get Material",
        description="Get a specific material by its ID",
    )
    async def get_by_id(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.get_by_id(request)

    @router.delete(
        "/{material_ids}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Materials")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Delete Materials",
        description="Delete one or more materials by their IDs",
    )
    async def delete_many(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.delete_many(request)

    @router.patch(
        "/copy",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Materials")),
            Depends(_validate("material_ids", "destination_id")),
        ],
        response_model=BaseResponseDto,
        status_code=201,
        summary="Copy Materials",
        description="Copy one or more materials to a destination folder",
    )
    async def copy_many(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.copy_many(request)

    @router.patch(
        "/move",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Materials")),
            Depends(_validate("material_ids", "destination_id")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Move Materials",
        description="Move one or more materials to a destination folder",
    )
    async def move_many(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.move_many(request)

    return router
