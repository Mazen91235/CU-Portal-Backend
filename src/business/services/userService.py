from sqlalchemy.orm import selectinload
from sqlalchemy import and_
from core.iServices.iUserService import IUserService
from core.entities.user import User
from core.entities.patient import Patient
from core.dtos.userDtos import (
    UserLoginResponseDto,
)
from core.dtos.baseDtos import BaseResponseDto
from core.iRepositories.iBaseRepository import IBaseRepository
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iServices.iHelperService import IHelperService
from core.entities.token import Token
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.hasher import Hasher
from core.utils.stringHandler import StringHandler
from core.utils.validator import Validator


class UserService(IUserService):
    def __init__(
        self,
        user_repository: IBaseRepository[User],
        patient_repository: IBaseRepository[Patient],
        token_repository: IBaseRepository[Token],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.user_repository = user_repository
        self.patient_repository = patient_repository
        self.token_repository = token_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.user_repository.begin_transaction()

    async def commit_transaction(self):
        await self.user_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.user_repository.rollback_transaction()

    # CRUD Functions
    async def find_one(
        self,
        data=None,
        includes=[],
        selects=[],
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=[],
        descending=False,
    ):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                    error=user_response.error,
                )

            user = user_response.data
            return BaseResponseDto(success=True, data=user)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while finding user - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding user",
                error=str(ex),
            )

    async def find(
        self,
        data=None,
        includes=[],
        selects=[],
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=[],
        descending=False,
        page=1,
        limit=50,
    ):
        return BaseResponseDto[None | list[User]](success=True, data=None)

    async def create(self, data):
        try:
            validate_email_response = Validator.validate_email(data.email)
            if not validate_email_response.success:
                return BaseResponseDto(
                    success=False,
                    code=validate_email_response.code,
                    data=None,
                    message=validate_email_response.message,
                )
            data.email = validate_email_response.data
            user_response = await self.user_repository.find_one(
                User.email == data.email
            )
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if user is not None:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="warning",
                    code=400,
                    message="Email already exists",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Email already exists",
                )
            validate_password_response = Validator.validate_password(data.password)
            if not validate_password_response.success:
                return BaseResponseDto(
                    success=False,
                    code=validate_password_response.code,
                    data=None,
                    message=validate_password_response.message,
                )
            data.password = Hasher.hash_password(data.password)
            create_response = await self.user_repository.create(data)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                    error=create_response.error,
                )
            user = create_response.data
            if not user:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to create user",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to create user",
                )
            token_str = StringHandler.generate_random_string(Token.SHORT_LENGTH)
            expires_at = TimezoneHandler.add_hours(User.VerificationToken.EXPIRE_HOURS)
            token = Token(
                token=token_str,
                user_id=user.id,
                type=Token.TokenType.EMAIL_VERIFICATION,
                expires_at=expires_at,
            )
            token_response = await self.token_repository.create(token)
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=None,
                    message=token_response.message,
                    error=token_response.error,
                )
            message = f"Please use the following token to verify your email: {token_str}. This token will expire in {User.VerificationToken.EXPIRE_HOURS} hours."
            email_response = await self.helper_service.send_email(
                to_email=user.email,
                subject="Email Verification",
                body=message,
            )
            if not email_response.success:
                return BaseResponseDto(
                    success=False,
                    code=email_response.code,
                    data=None,
                    message=email_response.message,
                    error=email_response.error,
                )
            await self.logger.log(
                action="Create",
                entity="User",
                level="info",
                code=201,
                message="User created successfully",
                source="UserService",
            )
            return BaseResponseDto[User | None](success=True, code=201, data=user)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while creating user - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating user",
                error=str(ex),
            )

    async def update(self, data):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="Update",
                    entity="User",
                    level="error",
                    code=404,
                    message="Logged in user not found",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found",
                )
            user.name = data.name
            update_response = await self.user_repository.update(user, ["name"])
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                    error=update_response.error,
                )
            await self.logger.log(
                action="Update",
                entity="User",
                level="info",
                code=200,
                message="User updated successfully",
                source="UserService",
            )
            return BaseResponseDto[User | None](success=True, data=user)
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while updating user - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating user",
                error=str(ex),
            )

    async def delete(self, data):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=False,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="Delete",
                    entity="User",
                    level="error",
                    code=404,
                    message="Logged in user not found",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="Logged in user not found",
                )
            patients_count_response = await self.patient_repository.count(
                Patient.user_id == user.id,
            )
            if not patients_count_response.success:
                return BaseResponseDto(
                    success=False,
                    code=patients_count_response.code,
                    data=False,
                    message=patients_count_response.message,
                    error=patients_count_response.error,
                )
            patients_count = patients_count_response.data
            if patients_count > 0:
                await self.logger.log(
                    action="Delete",
                    entity="User",
                    level="warning",
                    code=400,
                    message="User Has Patients",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="Cannot delete user with existing patients",
                )
            delete_response = await self.user_repository.delete(user)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=False,
                    message=delete_response.message,
                    error=delete_response.error,
                )
            await self.logger.log(
                action="Delete",
                entity="User",
                level="info",
                code=200,
                message="User deleted successfully",
                source="UserService",
            )
            return BaseResponseDto(success=True, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while deleting user - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while deleting user",
                error=str(ex),
            )

    # User Specific Functions
    async def _invalidate_tokens(self, user_id: int):
        try:
            tokens_response = await self.token_repository.find(
                Token.user_id == user_id,
            )
            if not tokens_response.success:
                return BaseResponseDto(
                    success=False,
                    code=tokens_response.code,
                    data=False,
                    message=tokens_response.message,
                    error=tokens_response.error,
                )
            tokens = tokens_response.data
            for token in tokens:
                delete_token_response = await self.token_repository.delete(token)
                if not delete_token_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=delete_token_response.code,
                        data=False,
                        message=delete_token_response.message,
                        error=delete_token_response.error,
                    )
            return BaseResponseDto(success=True, data=True)
        except Exception as ex:
            await self.logger.log(
                action="InvalidateTokens",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while invalidating tokens - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while invalidating tokens",
                error=str(ex),
            )

    async def verify_email(self, token):
        try:
            token_response = await self.token_repository.find_one(
                and_(
                    Token.token == token,
                    Token.type == Token.TokenType.EMAIL_VERIFICATION,
                    Token.expires_at > TimezoneHandler.now("UTC"),
                ),
                [selectinload(Token.user)],
            )

            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=False,
                    message=token_response.message,
                    error=token_response.error,
                )

            verification_token = token_response.data
            if verification_token is None:
                await self.logger.log(
                    action="VerifyEmail",
                    entity="User",
                    level="warning",
                    code=400,
                    message="Invalid or expired verification token",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="Invalid or expired verification token",
                )

            user = verification_token.user
            if user is None:
                await self.logger.log(
                    action="VerifyEmail",
                    entity="User",
                    level="warning",
                    code=404,
                    message="User not found for this token",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="User not found for this token",
                )

            if user.is_verified:
                await self.logger.log(
                    action="VerifyEmail",
                    entity="User",
                    level="info",
                    code=200,
                    message="Email is already verified",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="Email is already verified",
                )

            user.is_verified = True
            update_response = await self.user_repository.update(user, ["is_verified"])
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=False,
                    message=update_response.message,
                    error=update_response.error,
                )
            invalidate_tokens_response = await self._invalidate_tokens(user.id)
            if not invalidate_tokens_response.success:
                return BaseResponseDto(
                    success=False,
                    code=invalidate_tokens_response.code,
                    data=False,
                    message=invalidate_tokens_response.message,
                    error=invalidate_tokens_response.error,
                )

            await self.logger.log(
                action="VerifyEmail",
                entity="User",
                level="info",
                code=200,
                message="User email verified successfully",
                source="UserService",
            )

            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Email verified successfully",
            )

        except Exception as ex:
            await self.logger.log(
                action="VerifyEmail",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while verifying email - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while verifying email",
                error=str(ex),
            )

    async def login(self, email, password):
        try:
            validate_email_response = Validator.validate_email(email)
            if not validate_email_response.success:
                return BaseResponseDto[UserLoginResponseDto | None](
                    success=False,
                    code=validate_email_response.code,
                    data=None,
                    message=validate_email_response.message,
                )
            normalized_email = validate_email_response.data
            user_response = await self.user_repository.find_one(
                User.email == normalized_email
            )
            if not user_response.success:
                return BaseResponseDto[UserLoginResponseDto | None](
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                    error=user_response.error,
                )

            user = user_response.data
            if user is None:
                await self.logger.log(
                    action="Login",
                    entity="User",
                    level="warning",
                    code=404,
                    message="User not found with this email",
                    source="UserService",
                )
                return BaseResponseDto[UserLoginResponseDto | None](
                    success=False,
                    code=404,
                    data=None,
                    message="User not found",
                )

            if not user.is_verified:
                await self.logger.log(
                    action="Login",
                    entity="User",
                    level="warning",
                    code=403,
                    message="Email is not verified",
                    source="UserService",
                )
                return BaseResponseDto[UserLoginResponseDto | None](
                    success=False,
                    code=403,
                    data=None,
                    message="Email is not verified",
                )

            if not Hasher.verify_password(password, user.password):
                await self.logger.log(
                    action="Login",
                    entity="User",
                    level="warning",
                    code=401,
                    message="Invalid password provided",
                    source="UserService",
                )
                return BaseResponseDto[UserLoginResponseDto | None](
                    success=False,
                    code=401,
                    data=None,
                    message="Invalid email or password",
                )
            invalidate_tokens_response = await self._invalidate_tokens(user.id)
            if not invalidate_tokens_response.success:
                return BaseResponseDto[UserLoginResponseDto | None](
                    success=False,
                    code=invalidate_tokens_response.code,
                    data=None,
                    message=invalidate_tokens_response.message,
                    error=invalidate_tokens_response.error,
                )
            token_str = StringHandler.generate_random_string(Token.STANDARD_LENGTH)
            expires_at = TimezoneHandler.add_days(User.RefreshToken.EXPIRE_DAYS)
            token = Token(
                token=token_str,
                user_id=user.id,
                type=Token.TokenType.REFRESH_TOKEN,
                expires_at=expires_at,
            )
            token_response = await self.token_repository.create(token)
            if not token_response.success:
                return BaseResponseDto[UserLoginResponseDto | None](
                    success=False,
                    code=token_response.code,
                    data=None,
                    message=token_response.message,
                    error=token_response.error,
                )
            await self.logger.log(
                action="Login",
                entity="User",
                level="info",
                code=200,
                message="User logged in successfully",
                source="UserService",
            )
            response = UserLoginResponseDto(token=token_str, user=user)
            return BaseResponseDto[UserLoginResponseDto | None](
                success=True,
                code=200,
                data=response,
                message="Login successful",
            )
        except Exception as ex:
            await self.logger.log(
                action="Login",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while logging in - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto[UserLoginResponseDto | None](
                success=False,
                code=500,
                data=None,
                message="An error occurred while logging in",
                error=str(ex),
            )

    async def logout(self):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=False,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="Logout",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="Logged in user not found",
                )
            invalidate_tokens_response = await self._invalidate_tokens(user.id)
            if not invalidate_tokens_response.success:
                return BaseResponseDto(
                    success=False,
                    code=invalidate_tokens_response.code,
                    data=False,
                    message=invalidate_tokens_response.message,
                    error=invalidate_tokens_response.error,
                )
            await self.logger.log(
                action="Logout",
                entity="User",
                level="info",
                code=200,
                message="User logged out successfully",
                source="UserService",
            )

            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Logout successful",
            )

        except Exception as ex:
            await self.logger.log(
                action="Logout",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while logging out - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while logging out",
                error=str(ex),
            )

    async def forget_password(self, email):
        try:
            validate_email_response = Validator.validate_email(email)
            if not validate_email_response.success:
                return BaseResponseDto(
                    success=False,
                    code=validate_email_response.code,
                    data=False,
                    message=validate_email_response.message,
                )
            normalized_email = validate_email_response.data
            user_response = await self.user_repository.find_one(
                User.email == normalized_email
            )
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=False,
                    message=user_response.message,
                    error=user_response.error,
                )

            user = user_response.data
            if user is None:
                await self.logger.log(
                    action="ForgetPassword",
                    entity="User",
                    level="warning",
                    code=404,
                    message="User not found with this email",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="User not found",
                )
            invalidate_tokens_response = await self._invalidate_tokens(user.id)
            if not invalidate_tokens_response.success:
                return BaseResponseDto(
                    success=False,
                    code=invalidate_tokens_response.code,
                    data=False,
                    message=invalidate_tokens_response.message,
                    error=invalidate_tokens_response.error,
                )
            token_str = StringHandler.generate_random_string(Token.SHORT_LENGTH)
            expires_at = TimezoneHandler.add_hours(User.VerificationToken.EXPIRE_HOURS)
            token = Token(
                token=token_str,
                type=Token.TokenType.PASSWORD_RESET,
                expires_at=expires_at,
                user_id=user.id,
            )
            token_response = await self.token_repository.create(token)
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=False,
                    message=token_response.message,
                    error=token_response.error,
                )
            message = f"Please use the following token to reset your password: {token_str}. This token will expire in {User.VerificationToken.EXPIRE_HOURS} hours."
            email_response = await self.helper_service.send_email(
                to_email=user.email,
                subject="Password Reset Request",
                body=message,
            )
            if not email_response.success:
                return BaseResponseDto(
                    success=False,
                    code=email_response.code,
                    data=False,
                    message=email_response.message,
                    error=email_response.error,
                )
            await self.logger.log(
                action="ForgetPassword",
                entity="User",
                level="info",
                code=200,
                message="Password reset email sent successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Password reset email sent successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="ForgetPassword",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while processing forget password - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while processing forget password",
                error=str(ex),
            )

    async def reset_password(self, token, new_password):
        try:
            token_response = await self.token_repository.find_one(
                and_(
                    Token.token == token,
                    Token.type == Token.TokenType.PASSWORD_RESET,
                    Token.expires_at > TimezoneHandler.now("UTC"),
                ),
                [selectinload(Token.user)],
            )
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=False,
                    message=token_response.message,
                    error=token_response.error,
                )
            token = token_response.data
            if not token:
                await self.logger.log(
                    action="ResetPassword",
                    entity="User",
                    level="warning",
                    code=404,
                    message="token not found",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="token not found",
                )
            user = token.user
            validate_password_response = Validator.validate_password(new_password)
            if not validate_password_response.success:
                return BaseResponseDto(
                    success=False,
                    code=validate_password_response.code,
                    data=False,
                    message=validate_password_response.message,
                )
            user.password = Hasher.hash_password(new_password)
            user_response = await self.user_repository.update(user, ["password"])
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=False,
                    message=user_response.message,
                    error=user_response.error,
                )
            invalidate_tokens_response = await self._invalidate_tokens(user.id)
            if not invalidate_tokens_response.success:
                return BaseResponseDto(
                    success=False,
                    code=invalidate_tokens_response.code,
                    data=False,
                    message=invalidate_tokens_response.message,
                    error=invalidate_tokens_response.error,
                )
            await self.logger.log(
                action="ResetPassword",
                entity="User",
                level="info",
                code=201,
                message="Reset Password successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
            )
        except Exception as ex:
            await self.logger.log(
                action="ResetPassword",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while resetting password - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while resetting password",
                error=str(ex),
            )

    async def change_password(self, old_password, new_password):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=False,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="ChangePassword",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="Logged in user not found",
                )
            if not Hasher.verify_password(old_password, user.password):
                await self.logger.log(
                    action="ChangePassword",
                    entity="User",
                    level="warning",
                    code=400,
                    message=f"An error occurred while veryfing password",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="Invalid password",
                )
            validate_password_response = Validator.validate_password(new_password)
            if not validate_password_response.success:
                return BaseResponseDto(
                    success=False,
                    code=validate_password_response.code,
                    data=False,
                    message=validate_password_response.message,
                )
            user.password = Hasher.hash_password(new_password)
            user_response = await self.user_repository.update(user, ["password"])
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=False,
                    message=user_response.message,
                    error=user_response.error,
                )
            await self.logger.log(
                action="ChangePassword",
                entity="User",
                level="info",
                code=201,
                message="Changed Password successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
            )
        except Exception as ex:
            await self.logger.log(
                action="ChangePassword",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while changing password - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while changing password",
                error=str(ex),
            )

    async def resend_token(self, email):
        try:
            validate_email_response = Validator.validate_email(email)
            if not validate_email_response.success:
                return BaseResponseDto(
                    success=False,
                    code=validate_email_response.code,
                    data=None,
                    message=validate_email_response.message,
                )
            normalized_email = validate_email_response.data
            user_response = await self.user_repository.find_one(
                User.email == normalized_email
            )
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="warning",
                    code=404,
                    message="User not found with this email",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="User not found",
                )
            token_response = await self.token_repository.find_one(
                and_(
                    Token.user_id == user.id,
                    Token.type != Token.TokenType.REFRESH_TOKEN,
                    Token.expires_at > TimezoneHandler.now("UTC"),
                ),
                order_by=[Token.id],
                descending=True,
            )
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=None,
                    message=token_response.message,
                    error=token_response.error,
                )
            existing_token = token_response.data
            if not existing_token:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="warning",
                    code=404,
                    message="No valid token found for this user",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="No valid token found for this user",
                )
            invalidate_tokens_response = await self._invalidate_tokens(user.id)
            if not invalidate_tokens_response.success:
                return BaseResponseDto(
                    success=False,
                    code=invalidate_tokens_response.code,
                    data=None,
                    message=invalidate_tokens_response.message,
                    error=invalidate_tokens_response.error,
                )
            token_str = StringHandler.generate_random_string(Token.SHORT_LENGTH)
            expires_at = TimezoneHandler.add_hours(User.VerificationToken.EXPIRE_HOURS)
            new_token = Token(
                token=token_str,
                user_id=user.id,
                type=existing_token.type,
                expires_at=expires_at,
            )
            create_token_response = await self.token_repository.create(new_token)
            if not create_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_token_response.code,
                    data=None,
                    message=create_token_response.message,
                    error=create_token_response.error,
                )

            subject = ""
            message = ""
            if existing_token.type == Token.TokenType.EMAIL_VERIFICATION:
                subject = "Email Verification Token"
                message = f"Please use the following token to verify your email: {token_str}. This token will expire in {User.VerificationToken.EXPIRE_HOURS} hours."
            elif existing_token.type == Token.TokenType.PASSWORD_RESET:
                subject = "Password Reset Token"
                message = f"Please use the following token to reset your password: {token_str}. This token will expire in {User.VerificationToken.EXPIRE_HOURS} hours."
            email_response = await self.helper_service.send_email(
                to_email=user.email,
                subject=subject,
                body=message,
            )
            if not email_response.success:
                return BaseResponseDto(
                    success=False,
                    code=email_response.code,
                    data=None,
                    message=email_response.message,
                    error=email_response.error,
                )
            await self.logger.log(
                action="ResendToken",
                entity="User",
                level="info",
                code=200,
                message="Verification token resent successfully",
                source="UserService",
            )
            success_message = ""
            if existing_token.type == Token.TokenType.EMAIL_VERIFICATION:
                success_message = "Verification token resent successfully"
            elif existing_token.type == Token.TokenType.PASSWORD_RESET:
                success_message = "Password reset token resent successfully"
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message=success_message,
            )
        except Exception as ex:
            await self.logger.log(
                action="ResendToken",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while resending token - {str(ex)}",
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while resending token",
                error=str(ex),
            )
