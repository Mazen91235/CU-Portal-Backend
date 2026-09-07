from core.iControllers.iUserController import IUserController
from core.iServices.iUserService import IUserService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.cookieHandler import CookieHandler
from core.utils.parser import Parser
from core.utils.oauthHandler import OAuthHandler
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.jsonHandler import JSONHandler

# Entities & DTOs
from core.entities.user import User
from core.dtos.userDtos import (
    UserCreateDto,
    UserResponseDto,
    UserUpdateDto,
    UserSearchDto,
)


class UserController(IUserController):
    def __init__(self, user_service: IUserService, logger: IBaseLogger):
        self.user_service = user_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            response = await self.user_service.get_user_with_details(id)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            user = response.data
            if not user:
                await self.logger.log(
                    action="FindOne",
                    entity="User",
                    level="info",
                    code=404,
                    message="User not found",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="User not found",
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=user,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[UserSearchDto].generate_from_query(
                UserSearchDto, query
            )
            includes = query.includes
            selects = query.selects
            is_and = query.is_and
            starts_with = query.starts_with
            is_exact = query.is_exact
            order_by = query.order_by
            descending = query.descending
            page = query.page or 1
            limit = query.limit or 50

            response = await self.user_service.find(
                entity_search_dto,
                includes,
                selects,
                is_and,
                starts_with,
                is_exact,
                order_by,
                descending,
                page,
                limit,
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            users = response.data

            users_mapped = Mapper[User, UserResponseDto].map_list(
                users or [], UserResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=users_mapped,
                next_page=response.next_page,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.user_service.begin_transaction()
            if not data.agreed:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="You must agree to the terms and conditions to create an account",
                )
            user = Mapper[UserCreateDto, User].map(data, User)
            response = await self.user_service.create(user)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            token = response.data.token if response.data else None
            if not token:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to generate verification token",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            token_details = {
                "token": token,
                "can_resend_after": TimezoneHandler.add_minutes(1).isoformat(),
            }
            token_details_stringified = JSONHandler.stringify(token_details)
            response = ResponseHandler.generate_response(
                success=True,
                code=201,
                message="User created successfully, Please verify your email to complete the registration process",
            )
            CookieHandler.set_cookie(
                response,
                "saved_token",
                token_details_stringified,
                httponly=True,
                secure=True,
                expires=User.VerificationToken.EXPIRE_HOURS * 60 * 60,
                max_age=User.VerificationToken.EXPIRE_HOURS * 60 * 60,
            )
            await self.user_service.commit_transaction()
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, data):
        try:
            await self.user_service.begin_transaction()
            user = Mapper[UserUpdateDto, User].map(data, User)
            response = await self.user_service.update(user)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            user = response.data
            if not user:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to update user",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            user_mapped = Mapper[User, UserResponseDto].map(user, UserResponseDto, True)
            await self.user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=user_mapped,
                message="User updated successfully",
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    # User Specific Functions
    # Auth Functions
    async def verify_email(self, request, data):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.verify_email(data.token)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            response = ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Email verified successfully, you can now log in to your account",
            )
            CookieHandler.delete_cookie(response, "saved_token")
            await self.user_service.commit_transaction()
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="VerifyEmail",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def login_with_google(self, request):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.login_with_google()
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            response_data = response.data
            if not response_data:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="LoginWithGoogle",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to generate Google login URL",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            await self.user_service.commit_transaction()
            return await OAuthHandler.authorize_google_redirect(
                request,
                redirect_url=response_data.redirect_response_url,
                state=response_data.state,
                nonce=response_data.nonce,
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="LoginWithGoogle",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def change_google_account(self, request):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.change_google_account()
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            response_data = response.data
            if not response_data:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="ChangeGoogleAccount",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to generate Google login URL",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            await self.user_service.commit_transaction()
            return await OAuthHandler.authorize_google_redirect(
                request,
                redirect_url=response_data.redirect_response_url,
                state=response_data.state,
                nonce=response_data.nonce,
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="ChangeGoogleAccount",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def google_authentication_redirect(self, request):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.authenticate_with_google()
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            response_data = response.data
            if not response_data:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="GoogleAuthenticationRedirect",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to authenticate with Google",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            response = ResponseHandler.generate_redirect_response(
                response_data.redirect_url or ""
            )
            if response_data.user:
                CookieHandler.set_cookie(
                    response,
                    "token",
                    response_data.token,
                    httponly=True,
                    secure=True,
                    expires=response_data.token_expiration or 0,
                    max_age=response_data.token_expiration or 0,
                )
            await self.user_service.commit_transaction()
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="GoogleAuthenticationRedirect",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def is_logged_in(self, request):
        try:
            response = await self.user_service.get_current_user_id()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            user_id = response.data
            if not user_id:
                await self.logger.log(
                    action="IsLoggedIn",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to retrieve current user ID",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=401,
                    message="User is not logged in",
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="User is logged in",
            )
        except Exception as e:
            await self.logger.log(
                action="IsLoggedIn",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def logout(self, request):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.logout()
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            response = ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Logged out successfully",
            )
            CookieHandler.delete_cookie(response, "token")
            await self.user_service.commit_transaction()
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="Logout",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing logout",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing logout, please try again later",
            )

    async def get_token_details(self, request):
        try:
            token_details_stringified = CookieHandler.get_cookie(request, "saved_token")
            if not token_details_stringified:
                await self.logger.log(
                    action="GetTokenDetails",
                    entity="User",
                    level="warning",
                    code=400,
                    message="No saved token found in cookies for retrieving token details",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="No saved token found in cookies for retrieving token details",
                )
            token_details = JSONHandler.parse(token_details_stringified)
            if not token_details:
                await self.logger.log(
                    action="GetTokenDetails",
                    entity="User",
                    level="warning",
                    code=400,
                    message="Failed to parse saved token details from cookies for retrieving token details",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Failed to parse saved token details from cookies for retrieving token details",
                )
            token = str(token_details.get("token"))
            can_resend_after = TimezoneHandler.from_isoformat(
                str(token_details.get("can_resend_after"))
            )
            response = await self.user_service.get_token_details(token)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            token_details = response.data
            if not token_details:
                await self.logger.log(
                    action="GetTokenDetails",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to retrieve token details from service",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            token_details.can_resend_after = (
                (can_resend_after - TimezoneHandler.now("UTC")).total_seconds()
                if can_resend_after > TimezoneHandler.now("UTC")
                else 0
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=token_details,
            )
        except Exception as e:
            await self.logger.log(
                action="GetTokenDetails",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def resend_token(self, request):
        try:
            await self.user_service.begin_transaction()
            token_details_stringified = CookieHandler.get_cookie(request, "saved_token")
            if not token_details_stringified:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="warning",
                    code=400,
                    message="No saved token found in cookies for resending token",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="No saved token found in cookies for resending token",
                )
            token_details = JSONHandler.parse(token_details_stringified)
            if not token_details:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="warning",
                    code=400,
                    message="Failed to parse saved token details from cookies for resending token",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Failed to parse saved token details from cookies for resending token",
                )
            token = str(token_details.get("token"))
            can_resend_after = TimezoneHandler.from_isoformat(
                str(token_details.get("can_resend_after"))
            )
            remaining_time = (
                (can_resend_after - TimezoneHandler.now("UTC")).total_seconds()
                if can_resend_after > TimezoneHandler.now("UTC")
                else 0
            )
            if remaining_time > 0:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="warning",
                    code=429,
                    message=f"Token resend request is too soon, please wait {remaining_time:.0f} second{'' if remaining_time == 1 else 's'} before trying again",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=429,
                    message=f"Token resend request is too soon, please wait {remaining_time:.0f} second{'' if remaining_time == 1 else 's'} before trying again",
                )
            response = await self.user_service.resend_token(token)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            response_data = response.data
            if not response_data:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to resend token",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            await self.user_service.commit_transaction()
            response = ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Token resent successfully if email exists",
            )
            token_details["token"] = response_data.token
            token_details["can_resend_after"] = TimezoneHandler.add_minutes(
                1
            ).isoformat()
            token_details_stringified = JSONHandler.stringify(token_details)
            CookieHandler.set_cookie(
                response,
                "saved_token",
                token_details_stringified,
                httponly=True,
                secure=True,
                expires=User.VerificationToken.EXPIRE_HOURS * 60 * 60,
                max_age=User.VerificationToken.EXPIRE_HOURS * 60 * 60,
            )
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="ResendToken",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_google_stored_token(self, request, data):
        try:
            response = await self.user_service.get_google_stored_token(
                data.google_details_token
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            access_token = response.data
            if not access_token:
                await self.logger.log(
                    action="GetGoogleStoredToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to retrieve Google stored access token",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=access_token,
            )
        except Exception as e:
            await self.logger.log(
                action="GetGoogleStoredToken",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_google_access_token(self, request):
        try:
            response = await self.user_service.get_google_access_token()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            access_token = response.data
            if not access_token:
                await self.logger.log(
                    action="GetGoogleAccessToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to retrieve Google access token",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=access_token,
            )
        except Exception as e:
            await self.logger.log(
                action="GetGoogleAccessToken",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    # User Functions
    async def get_statistics(self, request, query):
        try:
            entity_search_dto = Generator[UserSearchDto].generate_from_query(
                UserSearchDto, query
            )
            response = await self.user_service.get_statistics(entity_search_dto)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            statistics = response.data
            if not statistics:
                await self.logger.log(
                    action="GetStatistics",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to retrieve user statistics",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=statistics,
            )
        except Exception as e:
            await self.logger.log(
                action="GetStatistics",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update_many(self, request, data):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.update_many(data)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Users updated successfully",
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="UpdateMany",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def suspend(self, request, id):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.suspend(id)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="User suspended successfully",
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="Suspend",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def unsuspend(self, request, id):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.unsuspend(id)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="User unsuspended successfully",
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="Unsuspend",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update_academic_data(self, request, data):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.update_academic_data(data)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="User academic data updated successfully",
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="UpdateAcademicData",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_current_user(self, request, query):
        try:
            includes = query.includes
            response = await self.user_service.get_current_user(includes)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            user = response.data
            if not user:
                await self.logger.log(
                    action="GetCurrentUser",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to retrieve current user",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            user_mapped = Mapper[User, UserResponseDto].map(user, UserResponseDto, True)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=user_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="GetCurrentUser",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_user_permissions(self, request):
        try:
            response = await self.user_service.get_user_permissions()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            permissions = response.data
            if not permissions:
                await self.logger.log(
                    action="GetUserPermissions",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to retrieve user permissions",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=permissions,
            )
        except Exception as e:
            await self.logger.log(
                action="GetUserPermissions",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def has_permissions(self, request, data):
        try:
            response = await self.user_service.has_permissions(data)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            has_permissions = response.data
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=has_permissions,
            )
        except Exception as e:
            await self.logger.log(
                action="HasPermissions",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def register_device(self, request, data):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.register_device(data.device_token)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="RegisterDevice",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def unregister_device(self, request, data):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.unregister_device(data.device_token)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="UnregisterDevice",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
