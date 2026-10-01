from fastapi import APIRouter, Request, Depends
from api.routes.customRoute import CustomRoute
from core.iControllers.iUserCompletionController import IUserCompletionController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userCompletionDtos import (
    UserCompletionCreateDto,
    UserCompletionResponseDto,
    UserCompletionSearchDto,
)
from core.models.queryModel import QueryModel
from core.utils.parser import Parser
from core.utils.cookieHandler import cookie_scheme


def create_user_completion_user_router(controller_provider, auth_middleware_provider):
    router = APIRouter(
        prefix="/completions", tags=["User Completions"], route_class=CustomRoute
    )

    def _get_controller() -> IUserCompletionController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

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

    @router.get(
        "/{user_completion_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[UserCompletionResponseDto],
        status_code=200,
        summary="Find User Completion",
        description="Find a user completion by its ID",
    )
    async def find_one_user_completion(
        user_completion_id: int,
        request: Request,
        controller: IUserCompletionController = Depends(_get_controller),
    ):
        return await controller.find_one(request, id=user_completion_id)

    @router.get(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[list[UserCompletionResponseDto]],
        status_code=200,
        summary="Find User Completions",
        description="Find user completions for the currently logged-in user based on query parameters",
    )
    async def find_user_completions(
        request: Request,
        query: QueryModel[UserCompletionSearchDto] = Depends(
            Parser.parse_query(QueryModel[UserCompletionSearchDto])
        ),
        controller: IUserCompletionController = Depends(_get_controller),
    ):
        return await controller.find(request, query=query)

    @router.post(
        "/",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[UserCompletionResponseDto],
        status_code=201,
        summary="Create User Completion",
        description="Mark a week item or task as completed for the currently logged-in user",
    )
    async def create_user_completion(
        data: UserCompletionCreateDto,
        request: Request,
        controller: IUserCompletionController = Depends(_get_controller),
    ):
        return await controller.create(request, data=data)

    @router.delete(
        "/{user_completion_id}",
        dependencies=[Depends(_is_logged_in), Depends(_is_ready)],
        response_model=BaseResponseDto[bool],
        status_code=200,
        summary="Delete User Completion",
        description="Delete a user completion by its ID",
    )
    async def delete_user_completion(
        user_completion_id: int,
        request: Request,
        controller: IUserCompletionController = Depends(_get_controller),
    ):
        return await controller.delete(request, id=user_completion_id)

    return router
