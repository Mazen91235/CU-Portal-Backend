from fastapi import APIRouter, Request, Depends
from core.iControllers.iUserController import IUserController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware


def create_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/users", tags=["Users"])

    def get_controller() -> IUserController:
        return controller_provider()

    def get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

    def get_validation_middleware() -> IValidationMiddleware:
        return validation_middleware_provider()

    async def is_logged_in(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(get_auth_middleware),
    ):
        return await auth_middleware.is_logged_in(request)

    async def is_logged_out(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(get_auth_middleware),
    ):
        return await auth_middleware.is_logged_out(request)

    def validate(*keys):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(
                get_validation_middleware
            ),
        ):
            return await validation_middleware.handle(request, *keys)

        return validate_request

    @router.get("/", dependencies=[Depends(is_logged_in)])
    async def find_one(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.find_one(request)

    @router.post(
        "/",
        dependencies=[
            Depends(is_logged_out),
            Depends(validate("name", "email", "password")),
        ],
    )
    async def create(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.create(request)

    @router.patch("/", dependencies=[Depends(is_logged_in), Depends(validate("name"))])
    async def update(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.update(request)

    @router.delete("/", dependencies=[Depends(is_logged_in)])
    async def delete(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.delete(request)

    @router.post(
        "/verify-email",
        dependencies=[Depends(is_logged_out), Depends(validate("token"))],
    )
    async def verify_email(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.verify_email(request)

    @router.post(
        "/login",
        dependencies=[Depends(is_logged_out), Depends(validate("email", "password"))],
    )
    async def login(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.login(request)

    @router.post("/logout", dependencies=[Depends(is_logged_in)])
    async def logout(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.logout(request)

    @router.post(
        "/forget-password",
        dependencies=[Depends(is_logged_out), Depends(validate("email"))],
    )
    async def forget_password(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.forget_password(request)

    @router.post(
        "/reset-password",
        dependencies=[
            Depends(is_logged_out),
            Depends(validate("token", "new_password")),
        ],
    )
    async def reset_password(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.reset_password(request)

    @router.post(
        "/change-password",
        dependencies=[
            Depends(is_logged_in),
            Depends(validate("old_password", "new_password")),
        ],
    )
    async def change_password(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.change_password(request)

    @router.post("/resend-token", dependencies=[Depends(is_logged_out)])
    async def resend_token(
        request: Request, controller: IUserController = Depends(get_controller)
    ):
        return await controller.resend_token(request)

    return router
