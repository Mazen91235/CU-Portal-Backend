from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iNoteController import INoteController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.noteDtos import (
    NoteCreateDto,
    NoteResponseDto,
    NoteUpdateDto,
    NoteSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_note_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/notes", tags=["User Notes"], route_class=CustomRoute)

    def _get_controller() -> INoteController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

    def _get_validation_middleware() -> IValidationMiddleware:
        return validation_middleware_provider()

    async def _is_logged_in(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
        refresh_token: str | None = Depends(cookie_scheme),
    ):
        return await auth_middleware.is_logged_in(request, refresh_token)

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
        ],
        response_model=BaseResponseDto[NoteResponseDto],
        status_code=200,
        summary="Find Note",
        description="Find a specific note by its ID",
    )
    async def find_one_note(
        note_id: int,
        request: Request,
        controller: INoteController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=note_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
        ],
        response_model=BaseResponseDto[list[NoteResponseDto]],
        status_code=200,
        summary="Find Notes",
        description="Find all notes for the currently logged-in user",
    )
    async def find_notes(
        request: Request,
        query: QueryModel[NoteSearchDto] = Depends(
            Parser.parse_query(QueryModel[NoteSearchDto])
        ),
        controller: INoteController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(
                _validate(
                    "title",
                )
            ),
        ],
        response_model=BaseResponseDto[NoteResponseDto],
        status_code=201,
        summary="Create Note",
        description="Create a new note",
    )
    async def create_note(
        data: NoteCreateDto,
        request: Request,
        controller: INoteController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{note_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(
                _validate(
                    "title",
                    "content",
                )
            ),
        ],
        response_model=BaseResponseDto[NoteResponseDto],
        status_code=200,
        summary="Update Note",
        description="Update an existing note by its ID",
    )
    async def update_note(
        note_id: int,
        data: NoteUpdateDto,
        request: Request,
        controller: INoteController = Depends(_get_controller),
    ):
        return await controller.update(request, id=note_id, data=data)

    @router.delete(
        "/{note_id}",
        dependencies=[
            Depends(_is_logged_in),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Delete Note",
        description="Delete a note by its ID",
    )
    async def delete_note(
        note_id: int,
        request: Request,
        controller: INoteController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=note_id)

    return router
