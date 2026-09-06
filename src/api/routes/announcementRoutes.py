from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iAnnouncementController import IAnnouncementController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.announcementDtos import (
    AnnouncementCreateDto,
    AnnouncementResponseDto,
    AnnouncementUpdateDto,
    AnnouncementSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_announcement_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/announcements", tags=["User Announcements"], route_class=CustomRoute
    )

    def _get_controller() -> IAnnouncementController:
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
        "/{announcement_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[AnnouncementResponseDto],
        status_code=200,
        summary="Find Announcement",
        description="Find a specific announcement by its ID if enrolled in the subject",
    )
    async def find_one_announcement(
        announcement_id: int,
        request: Request,
        controller: IAnnouncementController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=announcement_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[AnnouncementResponseDto]],
        status_code=200,
        summary="Find Announcements",
        description="Find all announcements for the currently logged in user based on enrolled subjects",
    )
    async def find_announcements(
        request: Request,
        query: QueryModel[AnnouncementSearchDto] = Depends(
            Parser.parse_query(QueryModel[AnnouncementSearchDto])
        ),
        controller: IAnnouncementController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    return router


def create_announcement_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(
        prefix="/announcements", tags=["Admin Announcements"], route_class=CustomRoute
    )

    def _get_controller() -> IAnnouncementController:
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
        "/{announcement_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Announcements")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[AnnouncementResponseDto],
        status_code=200,
        summary="Find Announcement",
        description="Find an announcement by its ID (Admin View)",
    )
    async def find_one_announcement(
        announcement_id: int,
        request: Request,
        controller: IAnnouncementController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=announcement_id)

    @router.get(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("View Announcements")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[list[AnnouncementResponseDto]],
        status_code=200,
        summary="Find Announcements",
        description="Find announcements based on query parameters (Admin View)",
    )
    async def find_announcements(
        request: Request,
        query: QueryModel[AnnouncementSearchDto] = Depends(
            Parser.parse_query(QueryModel[AnnouncementSearchDto])
        ),
        controller: IAnnouncementController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Add Announcements")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("title", "content", "subject_id")),
        ],
        response_model=BaseResponseDto[AnnouncementResponseDto],
        status_code=201,
        summary="Create Announcement",
        description="Create a new announcement for a specific subject",
    )
    async def create_announcement(
        data: AnnouncementCreateDto,
        request: Request,
        controller: IAnnouncementController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.patch(
        "/{announcement_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Edit Announcements")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
            Depends(_validate("title", "content", "subject_id")),
        ],
        response_model=BaseResponseDto[AnnouncementResponseDto],
        status_code=200,
        summary="Update Announcement",
        description="Update an existing announcement by its ID",
    )
    async def update_announcement(
        announcement_id: int,
        data: AnnouncementUpdateDto,
        request: Request,
        controller: IAnnouncementController = Depends(_get_controller),
    ):
        return await controller.update(request, id=announcement_id, data=data)

    @router.delete(
        "/{announcement_id}",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Delete Announcements")),
            Depends(_is_ready),
            Depends(_has_registered_subjects),
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete Announcement",
        description="Delete an announcement by its ID",
    )
    async def delete_announcement(
        announcement_id: int,
        request: Request,
        controller: IAnnouncementController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=announcement_id)

    return router
