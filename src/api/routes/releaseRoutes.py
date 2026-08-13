from fastapi import APIRouter, Request, Depends
from core.iControllers.iReleaseController import IReleaseController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iRequestLimitMiddleware import IRequestLimitMiddleware
from core.dtos.baseDtos import BaseResponseDto

# Admin (Write) Routes
def create_release_admin_router(controller_provider, auth_middleware_provider, rate_limit_provider):
    router = APIRouter(prefix="/releases", tags=["Admin Releases"])

    def _get_controller() -> IReleaseController: return controller_provider()
    def _get_auth_middleware() -> IAuthMiddleware: return auth_middleware_provider()
    def _get_rate_limit_middleware() -> IRequestLimitMiddleware: return rate_limit_provider()

    async def _is_logged_in(request: Request, auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware)):
        return await auth_middleware.is_logged_in(request)

    def _is_authorized(*permissions):
        async def authorized_request(request: Request, auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware)):
            return await auth_middleware.is_authorized(request, *permissions)
        return authorized_request

    async def _rate_limit(request: Request, rate_middleware: IRequestLimitMiddleware = Depends(_get_rate_limit_middleware)):
        return await rate_middleware.throttle(request)

    @router.post("", dependencies=[Depends(_is_logged_in), Depends(_rate_limit), Depends(_is_authorized("Manage Releases"))], response_model=BaseResponseDto)
    async def create_release(request: Request, controller: IReleaseController = Depends(_get_controller)):
        return await controller.create_release(request)

    @router.patch("/{release_id}", dependencies=[Depends(_is_logged_in), Depends(_rate_limit), Depends(_is_authorized("Manage Releases"))], response_model=BaseResponseDto)
    async def update_release(release_id: int, request: Request, controller: IReleaseController = Depends(_get_controller)):
        return await controller.update_release(request, release_id)

    @router.delete("/{release_id}", dependencies=[Depends(_is_logged_in), Depends(_rate_limit), Depends(_is_authorized("Manage Releases"))], response_model=BaseResponseDto)
    async def delete_release(release_id: int, request: Request, controller: IReleaseController = Depends(_get_controller)):
        return await controller.delete_release(request, release_id)

    return router


# Public/User (Read Only) Routes
def create_release_user_router(controller_provider, rate_limit_provider):
    router = APIRouter(prefix="/releases", tags=["Releases (History)"])

    def _get_controller() -> IReleaseController: return controller_provider()
    def _get_rate_limit_middleware() -> IRequestLimitMiddleware: return rate_limit_provider()

    async def _rate_limit(request: Request, rate_middleware: IRequestLimitMiddleware = Depends(_get_rate_limit_middleware)):
        return await rate_middleware.throttle(request)

    # Note: No is_logged_in or is_authorized so any user can see release notes
    @router.get("", dependencies=[Depends(_rate_limit)], response_model=BaseResponseDto)
    async def get_releases(request: Request, controller: IReleaseController = Depends(_get_controller)):
        return await controller.get_releases(request)

    @router.get("/{release_id}", dependencies=[Depends(_rate_limit)], response_model=BaseResponseDto)
    async def get_release(release_id: int, request: Request, controller: IReleaseController = Depends(_get_controller)):
        return await controller.get_release(request, release_id)

    return router