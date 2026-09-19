from fastapi import Request, HTTPException
from fastapi.security import APIKeyCookie
from business.contextVars.userContext import user_context
from business.contextVars.permissionsContext import permissions_context
from business.contextVars.requestContext import request_context
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iServices.iUserService import IUserService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.entities.user import User
from core.entities.token import Token
from core.dtos.userDtos import UserSearchDto
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.cachingHandler import CachingHandler

cookie_scheme = APIKeyCookie(name="token", auto_error=False)
caching_handler = CachingHandler()


class AuthMiddleware(IAuthMiddleware):
    def __init__(
        self,
        user_service: IUserService,
        token_repository,
        logger: IBaseLogger,
    ):
        self.user_service = user_service
        self.token_repository = token_repository
        self.logger = logger

    async def is_logged_in(
        self, request: Request, refresh_token: str | None = None, throw_error: bool = True
    ):
        try:
            if not refresh_token:
                token = request.query_params.get("token")
                if token:
                    token_data = await caching_handler.get(token)
                    if token_data and "token" in token_data:
                        refresh_token = token_data["token"]
                        await caching_handler.delete(token)
            if not refresh_token:
                await self.logger.log(
                    action="AuthCheck",
                    entity="User",
                    level="warning",
                    code=401,
                    message="No refresh token provided in request cookies",
                    source="AuthMiddleware",
                )
                if not throw_error:
                    return None
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: No refresh token provided",
                )

            token_response = await self.token_repository.find_one(
                (
                    (Token.token == refresh_token)
                    & (Token.token_type == Token.TokenType.REFRESH_TOKEN["value"])
                    & (Token.expires_at > TimezoneHandler.now("UTC"))
                    & (Token.is_valid.is_(True))
                )
            )
            if not token_response.success:
                if not throw_error:
                    return None
                raise HTTPException(
                    status_code=token_response.code or 500,
                    detail=token_response.message,
                )

            token_record = token_response.data
            user_id = token_record.user_id if token_record else None
            if not token_record or not user_id:
                await self.logger.log(
                    action="AuthCheck",
                    entity="User",
                    level="warning",
                    code=401,
                    message="Invalid or expired refresh token provided in request cookies",
                    source="AuthMiddleware",
                )
                if not throw_error:
                    return None
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Invalid or Expired refresh token",
                )

            user_response = await self.user_service.find_one(
                UserSearchDto(id=user_id),
                ["role.role_links.exact_role", "avatar"],
                is_and=True,
            )
            if not user_response.success:
                if not throw_error:
                    return None
                raise HTTPException(
                    status_code=user_response.code or 500, detail=user_response.message
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="AuthCheck",
                    entity="User",
                    level="warning",
                    code=401,
                    message="User associated with refresh token was not found",
                    source="AuthMiddleware",
                )
                if not throw_error:
                    return None
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: User associated with refresh token was not found",
                )

            user.refresh_token = refresh_token
            user_context.set(user)

            if (
                TimezoneHandler.get_abs_diff_in_days(token_record.expires_at)
                < User.RefreshToken.MINIMUM_DAYS
            ):
                update_refresh_token_response = await self.user_service.refresh_token()
                if (
                    update_refresh_token_response.success
                    and update_refresh_token_response.data
                ):
                    await self.logger.log(
                        action="RefreshToken",
                        entity="User",
                        level="info",
                        code=200,
                        message="Refresh token expiration extended successfully",
                        source="AuthMiddleware",
                    )

            user_permissions = (
                set([perm.name for perm in user.role.exact_roles])
                if user.role
                else set()
            )

            permissions_context.set(user_permissions)

            request.state.restrict_faculties = False
            request.state.restrict_departments = False
            request.state.restrict_years = False
            request.state.restrict_courses = False

            if any(
                [
                    x in request.url.path
                    for x in [
                        "/faculties",
                        "/departments",
                        "/years",
                        "/courses",
                        "/materials",
                    ]
                ]
            ):
                request_context.set(request)
                return None

            if (
                "/admin" not in request.url.path
                or "Access All Faculties" not in user_permissions
            ):
                request.state.restrict_faculties = True

            if (
                "/admin" not in request.url.path
                or "Access All Departments" not in user_permissions
            ):
                request.state.restrict_departments = True

            if (
                "/admin" not in request.url.path
                or "Access All Years" not in user_permissions
            ):
                request.state.restrict_years = True

            if (
                "/admin" not in request.url.path
                or "Access All Courses" not in user_permissions
            ):
                request.state.restrict_courses = True

            request_context.set(request)

            return None

        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="AuthCheck",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred during authentication check: {repr(ex)}",
                source="AuthMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error during authentication check",
            )

    async def is_logged_out(self, request: Request, refresh_token: str | None = None):
        try:
            if refresh_token:
                token_response = await self.token_repository.find_one(
                    (
                        (Token.token == refresh_token)
                        & (Token.token_type == Token.TokenType.REFRESH_TOKEN["value"])
                        & (Token.expires_at > TimezoneHandler.now("UTC"))
                        & (Token.is_valid.is_(True))
                    )
                )
                if not token_response.success:
                    raise HTTPException(
                        status_code=token_response.code or 500,
                        detail=token_response.message,
                    )
                if token_response.data:
                    await self.logger.log(
                        action="AuthCheck",
                        entity="User",
                        level="warning",
                        code=400,
                        message="User is already logged in with a valid refresh token",
                        source="AuthMiddleware",
                    )
                    raise HTTPException(
                        status_code=400,
                        detail="Bad Request: User is already logged in",
                    )

            return None

        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="AuthCheck",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred during authentication check: {repr(ex)}",
                source="AuthMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error during authentication check",
            )

    async def is_authorized(self, request: Request, *permissions):
        try:
            user_permissions = permissions_context.get()
            required_permissions = set(permissions)

            if not required_permissions.issubset(user_permissions):
                await self.logger.log(
                    action="AuthorizationCheck",
                    entity="User",
                    level="warning",
                    code=403,
                    message=f"User lacks required permissions: {required_permissions - user_permissions}",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: User does not have the required permissions",
                )

            return None

        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="AuthorizationCheck",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred during authorization check: {repr(ex)}",
                source="AuthMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error during authorization check",
            )

    async def is_ready(self, request: Request):
        try:
            user = user_context.get()
            if not user:
                await self.logger.log(
                    action="ReadyCheck",
                    entity="User",
                    level="warning",
                    code=401,
                    message="Unauthenticated request attempted ready check",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: You are not logged in",
                )

            if (
                not user.faculty_id
                or not user.department_id
                or not user.year_id
                or not user.study_type
                or not user.study_type.strip()
            ):
                await self.logger.log(
                    action="ReadyCheck",
                    entity="User",
                    level="warning",
                    code=403,
                    message="User not ready to use the system",
                    details={"user_id": user.id},
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=403,
                    detail="Please complete your profile to proceed",
                )

            if not user.status:
                await self.logger.log(
                    action="ReadyCheck",
                    entity="User",
                    level="warning",
                    code=403,
                    message="User not verified yet",
                    details={"user_id": user.id},
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=403,
                    detail="Your account is not verified yet. Please wait for an admin to verify your account",
                )

            return None

        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="ReadyCheck",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while validating user readiness: {repr(ex)}",
                source="AuthMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error during readiness check",
            )

    async def has_registered_subjects(self, request: Request):
        try:
            user = user_context.get()
            if not user:
                await self.logger.log(
                    action="RegisteredSubjectsCheck",
                    entity="User",
                    level="warning",
                    code=401,
                    message="Unauthenticated request attempted registered subjects check",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: You are not logged in",
                )

            user_response = await self.user_service.find_one(
                UserSearchDto(id=user.id),
                ["user_subject_links.subject"],
            )
            if not user_response.success:
                raise HTTPException(
                    status_code=user_response.code or 500,
                    detail=user_response.message,
                )
            user_with_subjects = user_response.data
            if not user_with_subjects or not user_with_subjects.subjects:
                await self.logger.log(
                    action="RegisteredSubjectsCheck",
                    entity="User",
                    level="warning",
                    code=403,
                    message="User has not registered any subjects",
                    details={"user_id": user.id},
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=403,
                    detail="You need to register for at least one subject to access this resource",
                )
            return None

        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="RegisteredSubjectsCheck",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while validating registered subjects: {repr(ex)}",
                source="AuthMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error during registered subjects check",
            )
