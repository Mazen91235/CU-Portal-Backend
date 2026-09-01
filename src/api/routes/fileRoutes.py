from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iFileController import IFileController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.utils.cookieHandler import cookie_scheme


def create_file_public_router(controller_provider):
    router = APIRouter(prefix="/files", tags=["Public Files"], route_class=CustomRoute)

    def _get_controller() -> IFileController:
        return controller_provider()

    @router.get(
        "/{file_id}/download",
        dependencies=[],
        summary="Download File",
        description="Download a file by its ID",
    )
    async def download_file(
        file_id: str,
        request: Request,
        controller: IFileController = Depends(_get_controller),
    ):
        return await controller.download(request, id=file_id)

    return router
