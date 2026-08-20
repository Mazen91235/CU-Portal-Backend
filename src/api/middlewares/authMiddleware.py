from fastapi import Request, HTTPException
from fastapi.security import APIKeyCookie
from business.contextVars.userContext import user_context
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iServices.iUserService import IUserService
from core.iServices.iRoleService import IRoleService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.entities.user import User
from core.dtos.userDtos import UserSearchDto
from core.dtos.roleDtos import RoleSearchDto
from core.utils.timezoneHandler import TimezoneHandler

cookie_scheme = APIKeyCookie(name="token", auto_error=False)


class AuthMiddleware(IAuthMiddleware):
    def __init__(
        self,
        user_service: IUserService,
        role_service: IRoleService,
        logger: IBaseLogger,
    ):
        self.user_service = user_service
        self.role_service = role_service
        self.logger = logger

    async def is_logged_in(self, request: Request, refresh_token: str | None = None):
        try:
            if not refresh_token:
                await self.logger.log(
                    action="AuthCheck",
                    entity="User",
                    level="warning",
                    code=401,
                    message="No refresh token provided in request cookies",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: No refresh token provided",
                )

            user_search_dto = UserSearchDto(
                refresh_token=refresh_token,
                # refresh_expire_at_from=TimezoneHandler.now("UTC"),
            )

            user_response = await self.user_service.find_one(
                user_search_dto,
                is_and=True,
            )

            if not user_response.success:
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
                    message="Invalid or Expired refresh token provided in request cookies",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Invalid or Expired refresh token",
                )

            if not user.refresh_token or not user.refresh_expire_at:
                user_context.set(user)
                return None

            if (
                TimezoneHandler.get_abs_diff_in_days(user.refresh_expire_at)
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

            user_context.set(user)

            return None

        except HTTPException:
            # Let expected HTTP exceptions pass through to the client
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
                user_search_entity_dto = UserSearchDto(
                    refresh_token=refresh_token,
                    refresh_expire_at_from=TimezoneHandler.now("UTC"),
                )
                user_response = await self.user_service.find_one(
                    user_search_entity_dto,
                    is_and=True,
                )
                if not user_response.success:
                    raise HTTPException(
                        status_code=user_response.code or 500,
                        detail=user_response.message,
                    )
                user = user_response.data
                if user:
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

            # Dependency passes successfully
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
            user = user_context.get()
            if not user:
                raise HTTPException(
                    status_code=401, detail="Unauthorized: User not logged in"
                )
            role_search_dto = RoleSearchDto(id=user.role_id)
            user_role_response = await self.role_service.find_one(
                role_search_dto, ["exact_roles"]
            )
            if not user_role_response.success:
                raise HTTPException(
                    status_code=user_role_response.code or 500,
                    detail=user_role_response.message,
                )
            user_role = user_role_response.data
            if not user_role:
                await self.logger.log(
                    action="AuthorizationCheck",
                    entity="User",
                    level="warning",
                    code=403,
                    message="User role not found for authorization check",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: User role not found for authorization check",
                )
            user_permissions = set([perm.name for perm in user_role.exact_roles])
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
                or not user.type
                or not user.type.strip()
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
