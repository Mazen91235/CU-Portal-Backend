from fastapi import APIRouter, Request, Depends
from core.iControllers.iPatientController import IPatientController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware


def create_patient_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/patients", tags=["Patients"])

    def get_controller() -> IPatientController:
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

    async def is_logged_in_patient(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(get_auth_middleware),
    ):
        return await auth_middleware.is_logged_in_patient(request)

    async def is_logged_out_patient(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(get_auth_middleware),
    ):
        return await auth_middleware.is_logged_out_patient(request)

    def validate(*keys):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(
                get_validation_middleware
            ),
        ):
            return await validation_middleware.handle(request, *keys)

        return validate_request

    @router.get("/data", dependencies=[Depends(is_logged_in_patient)])
    async def get_patient_data(
        request: Request, controller: IPatientController = Depends(get_controller)
    ):
        return await controller.get_patient_data(request)

    @router.get("/{id}", dependencies=[Depends(is_logged_in)])
    async def find_one(
        request: Request, controller: IPatientController = Depends(get_controller)
    ):
        return await controller.find_one(request)

    @router.get("/", dependencies=[Depends(is_logged_in)])
    async def find(
        request: Request, controller: IPatientController = Depends(get_controller)
    ):
        return await controller.find(request)

    @router.post(
        "/",
        dependencies=[
            Depends(is_logged_in),
            Depends(validate("name")),
        ],
    )
    async def create(
        request: Request, controller: IPatientController = Depends(get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/{id}", dependencies=[Depends(is_logged_in), Depends(validate("name"))]
    )
    async def update(
        request: Request, controller: IPatientController = Depends(get_controller)
    ):
        return await controller.update(request)

    @router.delete("/{id}", dependencies=[Depends(is_logged_in)])
    async def delete(
        request: Request, controller: IPatientController = Depends(get_controller)
    ):
        return await controller.delete(request)

    @router.post(
        "/login",
        dependencies=[Depends(is_logged_out_patient), Depends(validate("token"))],
    )
    async def login(
        request: Request, controller: IPatientController = Depends(get_controller)
    ):
        return await controller.login(request)

    return router
