from fastapi import APIRouter, Request, Depends
from core.iControllers.iNoteController import INoteController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.noteDtos import NoteResponseDto


def create_note_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/notes", tags=["User Notes"])

    def _get_controller() -> INoteController:
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
        "/{note_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[NoteResponseDto],
        status_code=200,
        summary="Find Note",
        description="Find a specific note by its ID",
    )
    async def find_one(  # type: ignore
        request: Request, controller: INoteController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[NoteResponseDto]],
        status_code=200,
        summary="Find Notes",
        description="Find all notes for the currently logged-in user",
    )
    async def find(  # type: ignore
        request: Request, controller: INoteController = Depends(_get_controller)
    ):
        return await controller.find(request)

    return router


def create_note_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/notes", tags=["Admin Notes"])

    def _get_controller() -> INoteController:
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

    @router.get(
        "/{note_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Notes")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[NoteResponseDto],
        status_code=200,
        summary="Find Note",
        description="Find a note by its ID (Admin View)",
    )
    async def find_one(  # type: ignore
        request: Request, controller: INoteController = Depends(_get_controller)
    ):
        return await controller.find_one(request)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Notes")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[NoteResponseDto]],
        status_code=200,
        summary="Find Notes",
        description="Find notes based on query parameters (Admin View)",
    )
    async def find(  # type: ignore
        request: Request, controller: INoteController = Depends(_get_controller)
    ):
        return await controller.find(request)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Manage Notes")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(
                _validate(
                    "content",
                    "date",
                )
            ),
        ],
        response_model=BaseResponseDto[NoteResponseDto],
        status_code=201,
        summary="Create Note",
        description="Create a new note",
    )
    async def create(  # type: ignore
        request: Request, controller: INoteController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.patch(
        "/{note_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Manage Notes")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(
                _validate(
                    "content",
                    "date",
                )
            ),
        ],
        response_model=BaseResponseDto[NoteResponseDto],
        status_code=200,
        summary="Update Note",
        description="Update an existing note by its ID",
    )
    async def update(  # type: ignore
        request: Request, controller: INoteController = Depends(_get_controller)
    ):
        return await controller.update(request)

    @router.delete(
        "/{note_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Manage Notes")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Note",
        description="Delete a note by its ID",
    )
    async def delete(  # type: ignore
        request: Request, controller: INoteController = Depends(_get_controller)
    ):
        return await controller.delete(request)

    return router
