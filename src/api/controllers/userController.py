from core.iControllers.iUserController import IUserController
from core.iServices.iUserService import IUserService
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.responseHandler import ResponseHandler
from core.utils.cookieHandler import CookieHandler

# Entities & DTOs
from core.entities.user import User
from core.dtos.userDtos import (
    UserRegisterDto,
    UserResponseDto,
    UserUpdateDto,
    UserLoginDto,
    UserVerifyEmailDto,
    UserForgotPasswordDto,
    UserResetPasswordDto,
    UserChangePasswordDto,
)


class UserController(IUserController):
    def __init__(self, user_service: IUserService, logger: IBaseLogger):
        self.user_service = user_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request):
        try:
            response = await self.user_service.find_one(None)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            user = Mapper[User, UserResponseDto].map(
                response.data, UserResponseDto, True
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
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def find(self, request):
        return ResponseHandler.generate_response(
            success=False,
            code=400,
            message="Finding multiple users is not supported",
        )

    async def create(self, request):
        try:
            await self.user_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserRegisterDto].generate(UserRegisterDto, payload)
            user = Mapper[UserRegisterDto, User].map(data, User)
            response = await self.user_service.create(user)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            user = Mapper[User, UserResponseDto].map(
                response.data, UserResponseDto, True
            )
            await self.user_service.commit_transaction()
            response = ResponseHandler.generate_response(
                success=True,
                code=201,
                data=user,
            )
            CookieHandler.set_cookie(
                response,
                "email",
                user.get("email") if isinstance(user, dict) else user.email,
                httponly=True,
                secure=True,
                expires=User.VerificationToken.EXPIRE_HOURS * 60 * 60,
                max_age=User.VerificationToken.EXPIRE_HOURS * 60 * 60,
            )
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def update(self, request):
        try:
            await self.user_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserUpdateDto].generate(UserUpdateDto, payload)
            user = Mapper[UserUpdateDto, User].map(data, User)
            response = await self.user_service.update(user)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            user = Mapper[User, UserResponseDto].map(
                response.data, UserResponseDto, True
            )
            await self.user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=user,
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def delete(self, request):
        try:
            await self.user_service.begin_transaction()
            response = await self.user_service.delete(None)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            response = ResponseHandler.generate_response(
                success=True,
                code=200,
                message="User deleted successfully",
            )
            CookieHandler.delete_cookie(response, "token")
            CookieHandler.delete_cookie(response, "email")
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    # User Specific Functions
    async def verify_email(self, request):
        try:
            await self.user_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserVerifyEmailDto].generate(UserVerifyEmailDto, payload)
            response = await self.user_service.verify_email(data.token)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            response = ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Email verified successfully",
            )
            CookieHandler.delete_cookie(response, "email")
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="VerifyEmail",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def login(self, request):
        try:
            await self.user_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserLoginDto].generate(UserLoginDto, payload)
            response = await self.user_service.login(data.email, data.password)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            user = response.data.user if response.data else None
            if not user:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="User not found",
                )
            user_mapped = Mapper[User, UserResponseDto].map(user, UserResponseDto, True)
            token = response.data.token if response.data else None
            response = ResponseHandler.generate_response(
                success=True,
                code=200,
                data=user_mapped,
            )
            CookieHandler.set_cookie(
                response,
                "token",
                token,
                httponly=True,
                secure=True,
                expires=User.RefreshToken.EXPIRE_DAYS * 24 * 60 * 60,
                max_age=User.RefreshToken.EXPIRE_DAYS * 24 * 60 * 60,
            )
            await self.user_service.commit_transaction()
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="Login",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
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
                message=f"An error occurred while processing logout - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing logout",
            )

    async def forget_password(self, request):
        try:
            await self.user_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserForgotPasswordDto].generate(
                UserForgotPasswordDto, payload
            )
            response = await self.user_service.forget_password(data.email)
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            response = ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Password reset instructions sent to email if it exists",
            )
            CookieHandler.set_cookie(
                response,
                "email",
                data.email,
                httponly=True,
                secure=True,
                expires=User.VerificationToken.EXPIRE_HOURS * 60 * 60,
                max_age=User.VerificationToken.EXPIRE_HOURS * 60 * 60,
            )
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="ForgetPassword",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def reset_password(self, request):
        try:
            await self.user_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserResetPasswordDto].generate(
                UserResetPasswordDto, payload
            )
            response = await self.user_service.reset_password(
                data.token, data.new_password
            )
            if not response.success:
                await self.user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_service.commit_transaction()
            response = ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Password reset successfully",
            )
            CookieHandler.delete_cookie(response, "email")
            return response
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="ResetPassword",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def change_password(self, request):
        try:
            await self.user_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserChangePasswordDto].generate(
                UserChangePasswordDto, payload
            )
            response = await self.user_service.change_password(
                data.old_password, data.new_password
            )
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
                message="Password changed successfully",
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="ChangePassword",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def resend_token(self, request):
        try:
            await self.user_service.begin_transaction()
            email = CookieHandler.get_cookie(request, "email")
            if not email:
                await self.user_service.rollback_transaction()
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="warning",
                    code=400,
                    message="No email found in cookies for resending token",
                    source="UserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="No email found in cookies for resending token",
                )
            response = await self.user_service.resend_token(email)
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
                message="Token resent successfully if email exists",
            )
        except Exception as e:
            await self.user_service.rollback_transaction()
            await self.logger.log(
                action="ResendToken",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="UserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )
