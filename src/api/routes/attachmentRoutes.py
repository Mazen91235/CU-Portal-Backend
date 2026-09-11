from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iAttachmentController import IAttachmentController
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware


def create_attachment_public_router(
    controller_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/attachments", tags=["Public Attachments"], route_class=CustomRoute
    )

    def _get_controller() -> IAttachmentController:
        return controller_provider()

    def _get_validation_middleware() -> IValidationMiddleware:
        return validation_middleware_provider()

    async def _validate_api_key(
        request: Request,
        validation_middleware: IValidationMiddleware = Depends(
            _get_validation_middleware
        ),
    ):
        return await validation_middleware.validate_api_key(request)

    @router.post(
        "/seed",
        dependencies=[
            # Depends(_validate_api_key),
        ],  # Set a timeout of 30 minutes for the seed operation
        summary="Seed Attachments",
        description="Seed the attachments table with initial data",
    )
    async def seed_attachments(
        request: Request,
        controller: IAttachmentController = Depends(_get_controller),
    ):
        return await controller.seed(request)

    @router.post(
        "/validate",
        dependencies=[
            Depends(_validate_api_key),
        ],  # Set a timeout of 30 minutes for the validate operation
        summary="Validate Attachments",
        description="Validate the attachments in the database",
    )
    async def validate_attachments(
        request: Request,
        start_idx: int,
        controller: IAttachmentController = Depends(_get_controller),
    ):
        return await controller.validate(request, start_idx)

    return router
