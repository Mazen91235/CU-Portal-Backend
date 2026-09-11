from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iSystemController import ISystemController
from core.dtos.baseDtos import BaseResponseDto


def create_system_public_router(controller_provider):
    router = APIRouter(
        prefix="/system", tags=["Public System"], route_class=CustomRoute
    )

    def _get_controller() -> ISystemController:
        return controller_provider()

    @router.get(
        "/health",
        dependencies=[],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Health Check",
        description="Check the health of the system",
    )
    async def health_check(
        request: Request,
        controller: ISystemController = Depends(_get_controller),
    ):
        return await controller.health_check(request)

    return router
