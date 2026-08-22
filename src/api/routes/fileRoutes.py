from fastapi import APIRouter, Request, Depends
from core.iControllers.iFileController import IFileController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from api.routes.customRoute import set_timeout


def create_file_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/files", tags=["Files"])

    def _get_controller() -> IFileController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

    async def _is_logged_in(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
    ):
        return await auth_middleware.is_logged_in(request)

    @router.get(
        "/{attachment_id}/download",
        dependencies=[Depends(_is_logged_in), Depends(set_timeout(30.0))],
        status_code=200,
        summary="Download File",
        description="Download an attachment's file content, streaming it from Google Drive",
    )
    async def download_file(
        request: Request, controller: IFileController = Depends(_get_controller)
    ):
        return await controller.download_file(request)

    return router
