from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute, allow_inactive
from core.iControllers.iUserController import IUserController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userDtos import (
    UserUpdateDto,
    UserResponseDto,
    UserSearchDto,
    UserUpdateUsersDto,
    UserHasPermissionsDto,
    UserUpdateAcademicDataDto,
    UserStatisticsResponseDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_user_user_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="", tags=["User"], route_class=CustomRoute)

    def _get_controller() -> IUserController:
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
        "/me",
        dependencies=[Depends(_is_logged_in), Depends(allow_inactive)],
        response_model=BaseResponseDto[UserResponseDto],
        status_code=200,
        summary="Get Current User",
        description="Get the currently logged in user",
    )
    async def get_current_user(
        request: Request,
        query: QueryModel[UserSearchDto] = Depends(
            Parser.parse_query(QueryModel[UserSearchDto])
        ),
        controller: IUserController = Depends(_get_controller),
    ):
        return await controller.get_current_user(request, query=query)

    @router.get(
        "/permissions",
        dependencies=[Depends(_is_logged_in), Depends(allow_inactive)],
        response_model=BaseResponseDto[list[str]],
        status_code=200,
        summary="Get User Permissions",
        description="Get the permissions of the currently logged in user",
    )
    async def get_user_permissions(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.get_user_permissions(request)

    @router.post(
        "/has-permissions",
        dependencies=[
            Depends(_is_logged_in),
            Depends(allow_inactive),
            Depends(_validate("required_permissions", "is_and")),
        ],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Check User Permissions",
        description="Check if the currently logged in user has the specified permissions",
    )
    async def has_permissions(
        data: UserHasPermissionsDto,
        request: Request,
        controller: IUserController = Depends(_get_controller),
    ):
        return await controller.has_permissions(request, data=data)

    @router.patch(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(allow_inactive),
            Depends(_validate("name")),
        ],
        response_model=BaseResponseDto[UserResponseDto],
        status_code=200,
        summary="Update User",
        description="Update the currently logged in user",
    )
    async def update_user(
        data: UserUpdateDto,
        request: Request,
        controller: IUserController = Depends(_get_controller),
    ):
        return await controller.update(request, data=data)

    @router.patch(
        "/academic-data",
        dependencies=[
            Depends(_is_logged_in),
            Depends(allow_inactive),
            Depends(_validate("faculty_id", "department_id", "year_id", "study_type")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Update Academic Data",
        description="Update the academic data of the currently logged in user",
    )
    async def update_academic_data(
        data: UserUpdateAcademicDataDto,
        request: Request,
        controller: IUserController = Depends(_get_controller),
    ):
        return await controller.update_academic_data(request, data=data)

    return router


def create_user_admin_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/users", tags=["Admin Users"], route_class=CustomRoute)

    def _get_controller() -> IUserController:
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
        "/statistics",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Users"))],
        response_model=BaseResponseDto[UserStatisticsResponseDto],
        status_code=200,
        summary="Get User Statistics",
        description="Get statistics for the users in the system, including total count, new users this month, percentage increase, active users, and pending users.",
    )
    async def get_user_statistics(
        request: Request,
        query: QueryModel[UserSearchDto] = Depends(
            Parser.parse_query(QueryModel[UserSearchDto])
        ),
        controller: IUserController = Depends(_get_controller),
    ):
        return await controller.get_statistics(request, query=query)

    @router.get(
        "/{user_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Users"))],
        response_model=BaseResponseDto[UserResponseDto],
        status_code=200,
        summary="Find User",
        description="Find a user by their ID",
    )
    async def find_one_user(
        user_id: int,
        request: Request,
        controller: IUserController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=user_id)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_authorized("View Users"))],
        response_model=BaseResponseDto[list[UserResponseDto]],
        status_code=200,
        summary="Find Users",
        description="Find users based on query parameters",
    )
    async def find_users(
        request: Request,
        query: QueryModel[UserSearchDto] = Depends(
            Parser.parse_query(QueryModel[UserSearchDto])
        ),
        controller: IUserController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.patch(
        "/",
        dependencies=[
            Depends(_is_logged_in),
            Depends(_is_authorized("Manage Users")),
            Depends(_validate("data_to_update")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Update Multiple Users",
        description="Update multiple users at once, including their approval status and role",
    )
    async def update_many_users(
        data: UserUpdateUsersDto,
        request: Request,
        controller: IUserController = Depends(_get_controller),
    ):
        return await controller.update_many(request, data=data)

    return router
