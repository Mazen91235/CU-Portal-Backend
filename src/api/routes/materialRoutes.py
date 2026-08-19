from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iMaterialController import IMaterialController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.materialDtos import MaterialResponseDto


def create_material_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/materials", tags=["Materials"], route_class=CustomRoute)

    def _get_controller() -> IMaterialController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

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
        "/{material_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[MaterialResponseDto],
        status_code=200,
        summary="Get Material",
        description="Get a specific material by its ID",
    )
    async def find_one(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[MaterialResponseDto],
        status_code=200,
        summary="Get Materials",
        description="Get a list of all materials",
    )
    async def find(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.get(
        "/{material_id}/parents",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[MaterialResponseDto]],
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
    router = APIRouter(prefix="/materials", tags=["Materials"], route_class=CustomRoute)

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
        "/{material_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Materials")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[MaterialResponseDto],
        status_code=200,
        summary="Get Material",
        description="Get a specific material by its ID",
    )
    async def find_one(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Materials")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[MaterialResponseDto],
        status_code=200,
        summary="Get Materials",
        description="Get a list of all materials",
    )
    async def find(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Materials")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "type", "subject_id")),
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
        "/{material_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Materials")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("name", "type")),
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

    @router.delete(
        "/{material_ids}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Materials")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
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
            Depends(_is_ready),
            Depends(_has_registered_subjects),
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
            Depends(_is_ready),
            Depends(_has_registered_subjects),
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

    @router.get(
        "/fetch-from-drive",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Materials")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("url", "subject_id")),
        ],
        response_model=BaseResponseDto[bool],
        status_code=201,
        summary="Fetch Materials From Drive",
        description="Fetch materials from a Google Drive URL and create them",
    )
    async def fetch_materials_from_drive(
        request: Request, controller: IMaterialController = Depends(_get_controller)
    ):
        return await controller.fetch_materials_from_drive(request)

    return router
