from typing import cast
from fastapi import APIRouter, Request, Depends, UploadFile, HTTPException
from core.iControllers.iPatientUserController import IPatientUserController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware


def create_patient_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/users", tags=["PatientUsers"])

    def get_controller() -> IPatientUserController:
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

    def validate(*keys):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(
                get_validation_middleware
            ),
        ):
            return await validation_middleware.handle(request, *keys)

        return validate_request

    def validate_files_count(expected_count: int):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(
                get_validation_middleware
            ),
        ):
            return await validation_middleware.validate_files_count(
                request, expected_count
            )

        return validate_request

    @router.post(
        "/identify",
        # dependencies=[Depends(is_logged_in_patient), Depends(validate_files_count(1))],
        dependencies=[Depends(validate_files_count(1))],
    )
    async def find_one(
        request: Request,
        controller: IPatientUserController = Depends(get_controller),
    ):
        files = getattr(request.state, "upload_files", [])
        file = cast(UploadFile, files[0])
        return await controller.find_one(request, file)

    @router.post(
        "/",
        dependencies=[
            Depends(is_logged_in_patient),
            Depends(validate("name", "relation")),
            Depends(validate_files_count(2)),
        ],
    )
    async def create(
        request: Request,
        controller: IPatientUserController = Depends(get_controller),
    ):
        files = getattr(request.state, "upload_files", [])
        return await controller.create(request, files)

    @router.delete("/{id}", dependencies=[Depends(is_logged_in)])
    async def delete(
        request: Request, controller: IPatientUserController = Depends(get_controller)
    ):
        return await controller.delete(request)

    return router
