import os
from datetime import timedelta
from typing import cast
from sqlalchemy import and_
from business.contextVars.requestContext import request_context
from core.iServices.iUserService import IUserService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.user import User
from core.entities.device import Device
from core.entities.pendingUser import PendingUser
from core.entities.role import Role
from core.entities.token import Token
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userDtos import (
    UserGetUserWithDetailsDto,
    UserLoginWithGoogleResponseDto,
    UserSignUpResponseDto,
    UserLoginResponseDto,
    UserStatisticsResponseDto,
    UserTokenDetailsResponseDto,
    UserResendTokenResponseDto,
)
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.fernetHandler import FernetHandler
from core.utils.stringHandler import StringHandler
from core.utils.validator import Validator
from core.utils.jwtHandler import JWTHandler
from core.utils.oauthHandler import OAuthHandler
from core.utils.generator import Generator


class UserService(IUserService):
    def __init__(
        self,
        user_repository: IBaseRepository[User],
        device_repository: IBaseRepository[Device],
        token_repository: IBaseRepository[Token],
        role_repository: IBaseRepository[Role],
        pending_user_repository: IBaseRepository[PendingUser],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.user_repository = user_repository
        self.device_repository = device_repository
        self.token_repository = token_repository
        self.role_repository = role_repository
        self.pending_user_repository = pending_user_repository
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
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                User, data, ["name", "email", "phone"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                User, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "User", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "User", order_by, descending
            )
            result = await self.user_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            user = result.data
            return BaseResponseDto(success=True, data=user)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while finding user",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding user",
            )

    async def find(
        self,
        data=None,
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
        page=1,
        limit=50,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                User, data, ["name", "email", "phone"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                User, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "User", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "User", order_by, descending
            )
            result = await self.user_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                page,
                limit,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            users = result.data
            return BaseResponseDto(success=True, data=users, next_page=result.next_page)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while finding users",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding users",
            )

    async def create(self, data):
        try:
            google_token_received = data.google_details_token
            if not google_token_received:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=400,
                    message="Google details token isn't provided",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Bad Request, Please try authorizing with Google again",
                )
            google_token_response = await self.token_repository.find_one(
                and_(
                    Token.token == google_token_received,
                    Token.token_type == Token.TokenType.GOOGLE_TOKEN["value"],
                    Token.expires_at > TimezoneHandler.now("UTC"),
                )
            )
            if not google_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=google_token_response.code,
                    data=None,
                    message=google_token_response.message,
                )
            google_token = cast(Token | None, google_token_response.data)
            if not google_token:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=400,
                    message="Google token is invalid or expired",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Bad Request, Please try authorizing with Google again",
                )
            google_token_details = google_token.details
            if not google_token_details or "token" not in google_token_details:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=400,
                    message="Google token details are missing or invalid",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Bad Request, Please try authorizing with Google again",
                )
            google_token.expires_at = TimezoneHandler.add_hours(-1)
            update_google_token_response = await self.token_repository.update(
                google_token, ["expires_at"]
            )
            if not update_google_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_google_token_response.code,
                    data=None,
                    message=update_google_token_response.message,
                )
            google_user_details_response = JWTHandler.decode_jwt(
                token=google_token_details.get("token"),
                secret_key=os.environ.get("GOOGLE_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            if not google_user_details_response.success:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=google_user_details_response.code or 500,
                    message="Failed to decode Google token details",
                    details={"error": google_user_details_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=google_user_details_response.code,
                    data=None,
                    message=google_user_details_response.message,
                )
            google_user_details = google_user_details_response.data
            if not google_user_details:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=400,
                    message="Google user details are missing or invalid",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Bad Request, Please try authorizing with Google again",
                )
            validate_email_response = Validator.validate_email(data.email, True)
            if not validate_email_response.success:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=validate_email_response.code or 500,
                    message="Invalid email address provided",
                    details={"error": validate_email_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=validate_email_response.code,
                    data=None,
                    message=validate_email_response.message,
                )
            validated_email = validate_email_response.data
            if not validated_email:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=400,
                    message="Email validation failed without a specific error",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Email validation failed, please check the email format.",
                )
            data.email = validated_email.normalized.lower()
            domain = validated_email.domain.lower()
            allowed_domain = Validator.is_allowed_domain(domain)
            needs_approval = not allowed_domain
            url = None
            if needs_approval:
                if not data.details.get("url"):
                    await self.logger.log(
                        action="Create",
                        entity="User",
                        level="warning",
                        code=400,
                        message="User didn't use an allowed email domain and didn't provide an approval Image",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="You must Upload your Approval Image or use Your University Email to register",
                    )
                url = data.details.get("url")
            if url:
                file_id = self.helper_service.get_file_id_from_url(url)
                if not file_id:
                    await self.logger.log(
                        action="Create",
                        entity="User",
                        level="warning",
                        code=400,
                        message="Invalid file URL provided for approval image",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid file uploaded for approval, please try again with a valid file.",
                    )
                file_response = await self.helper_service.fetch_from_drive(file_id)
                if not file_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="User",
                        level="warning",
                        code=file_response.code or 500,
                        message="Failed to fetch file from Google Drive",
                        details={"error": file_response.error},
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=file_response.code,
                        data=None,
                        message=file_response.message,
                    )
                file = file_response.data
                if not file:
                    await self.logger.log(
                        action="Create",
                        entity="User",
                        level="warning",
                        code=400,
                        message="File not found on Google Drive",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="The uploaded file could not be found, please try again.",
                    )
                if not self.helper_service.verify_file_type(
                    file.data.mime_type, "image"
                ):
                    await self.logger.log(
                        action="Create",
                        entity="User",
                        level="warning",
                        code=400,
                        message="Uploaded file is not an image",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="The uploaded file must be an image, please try again with a valid image file.",
                    )
                if not self.helper_service.verify_file_size(
                    file.data.size, User.MAX_ALLOWED_FILE_SIZE_B
                ):
                    await self.logger.log(
                        action="Create",
                        entity="User",
                        level="warning",
                        code=400,
                        message="Uploaded file exceeds maximum allowed size",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"The uploaded file exceeds the maximum allowed size of {User.MAX_ALLOWED_FILE_SIZE_MB} MB, please try again with a smaller file.",
                    )
            data.details.pop("url", None)
            email_exists_response = await self.user_repository.find_one(
                User.email == data.email
            )
            if not email_exists_response.success:
                return BaseResponseDto(
                    success=False,
                    code=email_exists_response.code,
                    data=None,
                    message=email_exists_response.message,
                )
            email_exists = email_exists_response.data
            if email_exists:
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
            phone_exists_response = await self.user_repository.find_one(
                User.phone == data.phone
            )
            if not phone_exists_response.success:
                return BaseResponseDto(
                    success=False,
                    code=phone_exists_response.code,
                    data=None,
                    message=phone_exists_response.message,
                )
            phone_exists = phone_exists_response.data
            if phone_exists:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="warning",
                    code=400,
                    message="Phone number already exists",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Phone number already exists",
                )
            if not Validator.is_valid_phone_number(data.phone):
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="warning",
                    code=400,
                    message="Invalid phone number format",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid phone number format, please provide a valid phone number.",
                )
            data.google_id = google_user_details.get("google_id")
            data.google_name = google_user_details.get("google_name")
            data.google_email = google_user_details.get("google_email")
            data.google_avatar = google_user_details.get("google_avatar")
            data.google_refresh_token = google_user_details.get("google_refresh_token")
            json_user_data = {
                k: v
                for k, v in data.__dict__.items()
                if v is not None and not k.startswith("_")
            }
            encoded_json_user_data_response = JWTHandler.encode_jwt(
                json_user_data,
                os.environ.get("USER_TOKEN_SECRET_KEY"),
                algorithm="HS256",
            )
            if not encoded_json_user_data_response.success:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to encode user data into JWT",
                    details={"error": encoded_json_user_data_response.message},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=encoded_json_user_data_response.code,
                    data=None,
                    message=encoded_json_user_data_response.message,
                )
            encoded_json_user_data = encoded_json_user_data_response.data
            if not encoded_json_user_data:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=500,
                    message="Encoded user data is None after JWT encoding",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while processing user data, please try again.",
                )
            token_str = StringHandler.generate_random_number(Token.SHORT_LENGTH)
            expires_at = TimezoneHandler.add_hours(User.VerificationToken.EXPIRE_HOURS)
            token = Token(
                token=token_str,
                details={
                    "user": encoded_json_user_data,
                    "pending_approval": url if needs_approval else None,
                },
                token_type=Token.TokenType.EMAIL_VERIFICATION["value"],
                expires_at=expires_at,
                is_valid=True,
            )
            created_token_response = await self.token_repository.create(token)
            if not created_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=created_token_response.code,
                    data=None,
                    message=created_token_response.message,
                )
            created_token = created_token_response.data
            if not created_token:
                await self.logger.log(
                    action="Create",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to create verification token, no token returned after creation",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating verification token, please try again.",
                )
            message = f"Please use the following code to verify your email: {token_str}. This code will expire in {User.VerificationToken.EXPIRE_HOURS} hour{f"s" if User.VerificationToken.EXPIRE_HOURS > 1 else ''}."
            email_response = await self.helper_service.send_email(
                to_email=data.email,
                subject="CU - Portal - Verify Email",
                body=message,
            )
            if not email_response.success:
                return BaseResponseDto(
                    success=False,
                    code=email_response.code,
                    data=None,
                    message=email_response.message,
                )
            await self.logger.log(
                action="Create",
                entity="User",
                level="info",
                code=201,
                message="User created successfully",
                source="UserService",
            )
            response = UserSignUpResponseDto(token=FernetHandler.encrypt(token_str))
            return BaseResponseDto(success=True, code=201, data=response)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while creating user",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating user",
            )

    async def update(self, data):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Update",
                    entity="User",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged-in user",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Update",
                    entity="User",
                    level="error",
                    code=401,
                    message="No logged-in user found in the request context",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="Unauthorized, please log in to update your profile.",
                )
            avatar = logged_in_user.avatar
            should_remove = None
            if (
                data.details
                and data.details.get("avatar")
                and data.details.get("avatar") != logged_in_user.google_avatar
                and (not avatar or data.details.get("avatar") != avatar.url)
            ):
                should_remove = avatar
                avatar.url = data.details.get("avatar")
            logged_in_user.name = data.name
            logged_in_user.details = data.details
            logged_in_user.details.pop("avatar", None)
            update_user_response = await self.user_repository.update(
                logged_in_user, ["name", "details"]
            )
            if not update_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_user_response.code,
                    data=None,
                    message=update_user_response.message,
                )
            updated_user = update_user_response.data
            if not updated_user:
                await self.logger.log(
                    action="Update",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to update user, no user returned after update",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating user, please try again.",
                )
            if should_remove:
                await self.helper_service.delete_attachment(attachment=should_remove)
                created_attachment_response = (
                    await self.helper_service.create_attachment(
                        is_file=True,
                        url=avatar.url or "",
                        author_id=logged_in_user.id,
                        source_name="user_id",
                        source_id=logged_in_user.id,
                    )
                )
                if not created_attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="User",
                        level="warning",
                        code=created_attachment_response.code or 500,
                        message="Failed to create attachment for new avatar",
                        details={"error": created_attachment_response.error},
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=created_attachment_response.code,
                        data=None,
                        message=created_attachment_response.message,
                    )
                created_attachment = created_attachment_response.data
                if not created_attachment:
                    await self.logger.log(
                        action="Update",
                        entity="User",
                        level="warning",
                        code=500,
                        message="Failed to create attachment for new avatar, no attachment returned after creation",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating attachment for new avatar, please try again.",
                    )
                logged_in_user.avatar_id = created_attachment.id
                update_user_with_avatar_response = await self.user_repository.update(
                    logged_in_user, ["avatar_id"]
                )
                if not update_user_with_avatar_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=update_user_with_avatar_response.code,
                        data=None,
                        message=update_user_with_avatar_response.message,
                    )
                updated_user = update_user_with_avatar_response.data
                if not updated_user:
                    await self.logger.log(
                        action="Update",
                        entity="User",
                        level="error",
                        code=500,
                        message="Failed to update user with new avatar, no user returned after update",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating user with new avatar, please try again.",
                    )
            await self.logger.log(
                action="Update",
                entity="User",
                level="info",
                code=200,
                message="User updated successfully",
                source="UserService",
            )
            return BaseResponseDto(success=True, data=updated_user)
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while updating user",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating user",
            )

    # User Specific Functions
    async def _invalidate_current_token(self, refresh_token: str | None):
        try:
            if not refresh_token:
                return BaseResponseDto(success=True, data=True)

            token_response = await self.token_repository.find_one(
                and_(
                    Token.token == refresh_token,
                    Token.token_type == Token.TokenType.REFRESH_TOKEN["value"],
                )
            )
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=False,
                    message=token_response.message,
                )

            token_record = token_response.data
            if token_record:
                delete_response = await self.token_repository.delete(token_record)
                if not delete_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=delete_response.code,
                        data=False,
                        message=delete_response.message,
                    )

            return BaseResponseDto(success=True, data=True)
        except Exception as ex:
            await self.logger.log(
                action="InvalidateCurrentToken",
                entity="User",
                level="error",
                code=500,
                message="An error occurred while invalidating current refresh token",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while invalidating current refresh token",
            )

    async def _login(
        self, google_id: str, google_refresh_token: str, redirect_url: str
    ):
        try:
            user_response = await self.user_repository.find_one(
                User.google_id == google_id
            )
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="Login",
                    entity="User",
                    level="warning",
                    code=404,
                    message="User not found with this Google ID",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="User not found",
                )

            refresh_token = StringHandler.generate_random_string(
                Token.STANDARD_LENGTH
            )
            expires_at = TimezoneHandler.add_days(User.RefreshToken.EXPIRE_DAYS)
            refresh_token_record = Token(
                user_id=user.id,
                token=refresh_token,
                token_type=Token.TokenType.REFRESH_TOKEN["value"],
                expires_at=expires_at,
                is_valid=True,
            )
            create_token_response = await self.token_repository.create(
                refresh_token_record
            )
            if not create_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_token_response.code,
                    data=None,
                    message=create_token_response.message,
                )
            created_token = create_token_response.data
            if not created_token:
                await self.logger.log(
                    action="Login",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to create refresh token",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while logging in user, please try again.",
                )

            user.google_refresh_token = google_refresh_token
            update_user_response = await self.user_repository.update(
                user, ["google_refresh_token"]
            )
            if not update_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_user_response.code,
                    data=None,
                    message=update_user_response.message,
                )
            updated_user = update_user_response.data or user

            await self.logger.log(
                action="Login",
                entity="User",
                level="info",
                code=200,
                message="User logged in successfully",
                source="UserService",
            )
            response = UserLoginResponseDto(
                user=updated_user,
                token=refresh_token,
                redirect_url=redirect_url,
                token_expiration=User.RefreshToken.EXPIRE_DAYS
                * 24
                * 60
                * 60,  # Convert days to seconds
            )
            return BaseResponseDto(success=True, code=200, data=response)
        except Exception as ex:
            await self.logger.log(
                action="Login",
                entity="User",
                level="error",
                code=500,
                message="An error occurred while logging in user",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while logging in user",
            )

    async def get_user_with_details(self, user_id):
        try:
            response = await self.user_repository.execute_stored_function(
                "get_user_with_details",
                {"p_user_id": user_id},
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                )
            response_data = response.data
            if not response_data:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="User not found",
                )
            result = Generator[UserGetUserWithDetailsDto].generate(
                UserGetUserWithDetailsDto, response_data
            )
            return BaseResponseDto(success=True, data=result)
        except Exception as ex:
            await self.logger.log(
                action="GetUserWithDetails",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while fetching user details",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching user details",
            )

    async def verify_email(self, token):
        try:
            token_response = await self.token_repository.find_one(
                and_(
                    Token.token == token,
                    Token.token_type == Token.TokenType.EMAIL_VERIFICATION["value"],
                    Token.expires_at > TimezoneHandler.now("UTC"),
                ),
            )
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=False,
                    message=token_response.message,
                )
            token = token_response.data
            if not token:
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
            token_details = token.details
            encoded_user_data = token_details.get("user") if token_details else None
            if not token_details or not encoded_user_data:
                await self.logger.log(
                    action="VerifyEmail",
                    entity="User",
                    level="warning",
                    code=400,
                    message="Token details are missing or invalid",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="User data not found in token details",
                )
            decoded_user_data_response = JWTHandler.decode_jwt(
                token=encoded_user_data,
                secret_key=os.environ.get("USER_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            if not decoded_user_data_response.success:
                await self.logger.log(
                    action="VerifyEmail",
                    entity="User",
                    level="error",
                    code=decoded_user_data_response.code or 500,
                    message="Failed to decode user data from token",
                    details={"error": decoded_user_data_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="Failed to Retrieve user data from token, please try again.",
                )
            user_data = decoded_user_data_response.data
            if not user_data:
                await self.logger.log(
                    action="VerifyEmail",
                    entity="User",
                    level="error",
                    code=400,
                    message="Decoded user data is None after JWT decoding",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="Failed to Retrieve user data from token, please try again.",
                )
            token.expires_at = TimezoneHandler.add_hours(-1)
            update_token_response = await self.token_repository.update(
                token, ["expires_at"]
            )
            if not update_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_token_response.code,
                    data=False,
                    message=update_token_response.message,
                )
            user_role_response = await self.role_repository.find_one(
                Role.name == "user"
            )
            if not user_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_role_response.code,
                    data=False,
                    message=user_role_response.message,
                )
            user_role = user_role_response.data
            if not user_role:
                await self.logger.log(
                    action="VerifyEmail",
                    entity="User",
                    level="error",
                    code=500,
                    message="User role not found in the database",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=False,
                    message="An error occurred while verifying email, please try again.",
                )
            pending_approval_url = token_details.get("pending_approval")
            user = User(
                name=user_data.get("name"),
                email=user_data.get("email"),
                phone=user_data.get("phone"),
                gender=user_data.get("gender"),
                is_early_access=user_data.get("is_early_access"),
                google_id=user_data.get("google_id"),
                google_name=user_data.get("google_name"),
                google_email=user_data.get("google_email"),
                google_avatar=user_data.get("google_avatar"),
                google_refresh_token=FernetHandler.encrypt(
                    user_data.get("google_refresh_token") or ""
                ),
                role=user_role,
                status=True if not pending_approval_url else False,
            )
            create_user_response = await self.user_repository.create(user)
            if not create_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_user_response.code,
                    data=False,
                    message=create_user_response.message,
                )
            created_user = create_user_response.data
            if not created_user:
                await self.logger.log(
                    action="VerifyEmail",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to create user after email verification",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=False,
                    message="An error occurred while creating user after email verification",
                )
            if pending_approval_url:
                pending_user = PendingUser(
                    user_id=created_user.id,
                )
                create_pending_user_response = (
                    await self.pending_user_repository.create(pending_user)
                )
                if not create_pending_user_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=create_pending_user_response.code,
                        data=False,
                        message=create_pending_user_response.message,
                    )
                created_pending_user = create_pending_user_response.data
                if not created_pending_user:
                    await self.logger.log(
                        action="VerifyEmail",
                        entity="PendingUser",
                        level="error",
                        code=500,
                        message="Failed to create pending user after email verification",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=False,
                        message="An error occurred while creating pending user after email verification",
                    )
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=pending_approval_url,
                    author_id=created_user.id,
                    source_name="pending_user_id",
                    source_id=created_pending_user.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="VerifyEmail",
                        entity="Attachment",
                        level="error",
                        code=attachment_response.code or 500,
                        message=attachment_response.message
                        or "An error occurred while creating attachment for pending user",
                        details={"error": attachment_response.error},
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code,
                        data=False,
                        message=attachment_response.message
                        or "An error occurred while creating attachment for pending user",
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="VerifyEmail",
                        entity="Attachment",
                        level="error",
                        code=500,
                        message="Failed to create attachment for pending user after email verification",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=False,
                        message="An error occurred while creating attachment for pending user after email verification",
                    )
            await self.logger.log(
                action="VerifyEmail",
                entity="User",
                level="info",
                code=200,
                message="User email verified and user created successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Email verified successfully, you can now log in.",
            )
        except Exception as ex:
            await self.logger.log(
                action="VerifyEmail",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while verifying email",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while verifying email",
            )

    async def login_with_google(self):
        try:
            await self.logout()
            request = request_context.get()
            is_localhost = "localhost" in (request.url.hostname or "")
            redirect_response_url = (
                ("https://" if not is_localhost else "http://")
                + (request.url.hostname or "")
                + (f":{request.url.port}" if request.url.port else "")
                + "/auth/google-authentication-redirect"
            )
            google_client = OAuthHandler.create_google_client()
            state = StringHandler.generate_random_string(User.GoogleToken.TOKEN_LENGTH)
            nonce = StringHandler.generate_random_string(User.GoogleToken.TOKEN_LENGTH)
            state_token = Token(
                token=state,
                token_type=Token.TokenType.GOOGLE_TOKEN["value"],
                expires_at=TimezoneHandler.add_hours(User.GoogleToken.EXPIRE_HOURS),
                details={"nonce": nonce},
                is_valid=True,
            )
            create_token_response = await self.token_repository.create(state_token)
            if not create_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_token_response.code,
                    data=None,
                    message=create_token_response.message,
                )
            created_token = create_token_response.data
            if not created_token:
                await self.logger.log(
                    action="LoginWithGoogle",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to create state token for Google login",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while initiating Google login, please try again.",
                )
            await self.logger.log(
                action="LoginWithGoogle",
                entity="User",
                level="info",
                code=200,
                message="Initiating Google login",
                source="UserService",
            )
            response = UserLoginWithGoogleResponseDto(
                redirect_response_url=redirect_response_url, state=state, nonce=nonce
            )
            return BaseResponseDto(success=True, code=200, data=response)
        except Exception as ex:
            await self.logger.log(
                action="LoginWithGoogle",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while logging in",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while logging in",
            )

    async def change_google_account(self):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="ChangeGoogleAccount",
                    entity="User",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged-in user for Google account change",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="ChangeGoogleAccount",
                    entity="User",
                    level="error",
                    code=401,
                    message="No logged-in user found in the request context for Google account change",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="Unauthorized, please log in to change your Google account.",
                )
            request = request_context.get()
            is_localhost = "localhost" in (request.url.hostname or "")
            redirect_response_url = (
                ("https://" if not is_localhost else "http://")
                + (request.url.hostname or "")
                + (f":{request.url.port}" if request.url.port else "")
                + "/auth/google-authentication-redirect"
            )
            google_client = OAuthHandler.create_google_client()
            state = StringHandler.generate_random_string(User.GoogleToken.TOKEN_LENGTH)
            nonce = StringHandler.generate_random_string(User.GoogleToken.TOKEN_LENGTH)
            state_token = Token(
                user_id=logged_in_user.id,
                token=state,
                token_type=Token.TokenType.GOOGLE_TOKEN["value"],
                expires_at=TimezoneHandler.add_hours(User.GoogleToken.EXPIRE_HOURS),
                details={"nonce": nonce},
                is_valid=True,
            )
            create_token_response = await self.token_repository.create(state_token)
            if not create_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_token_response.code,
                    data=None,
                    message=create_token_response.message,
                )
            created_token = create_token_response.data
            if not created_token:
                await self.logger.log(
                    action="ChangeGoogleAccount",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to create state token for Google account change",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while initiating Google account change, please try again.",
                )
            await self.logger.log(
                action="ChangeGoogleAccount",
                entity="User",
                level="info",
                code=200,
                message="Initiating Google account change",
                source="UserService",
            )
            response = UserLoginWithGoogleResponseDto(
                redirect_response_url=redirect_response_url, state=state, nonce=nonce
            )
            return BaseResponseDto(success=True, code=200, data=response)
        except Exception as ex:
            await self.logger.log(
                action="ChangeGoogleAccount",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while changing Google account",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while changing Google account",
            )

    async def authenticate_with_google(self):
        try:
            request = request_context.get()
            redirect_url = os.environ.get("FRONTEND_URL")
            if "localhost" in (request.url.hostname or ""):
                redirect_url = os.environ.get("FRONTEND_URL_LOCALHOST")
            requested_scopes = [
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/drive.file",
            ]
            details = {
                "cookies": {k: v for k, v in request.cookies.items()},
                "session": {k: v for k, v in request.session.items()},
            }
            oauth_state = request.query_params.get("state")
            state_token_response = await self.token_repository.find_one(
                and_(
                    Token.token == oauth_state,
                    Token.token_type == Token.TokenType.GOOGLE_TOKEN["value"],
                    Token.expires_at > TimezoneHandler.now("UTC"),
                )
            )
            if not state_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=state_token_response.code,
                    data=None,
                    message=state_token_response.message,
                )
            state_token = state_token_response.data
            if not state_token:
                await self.logger.log(
                    action="AuthenticateWithGoogle",
                    entity="User",
                    level="warning",
                    code=400,
                    message="Invalid or expired state token for Google authentication",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid or expired Google Authentication, please try again.",
                )
            details["nonce"] = (
                state_token.details.get("nonce") if state_token.details else None
            )
            user_id = state_token.user_id
            token = await OAuthHandler.authorize_google_access_token(
                request,
                nonce=details.get("nonce"),
            )
            granted_scopes = token.get("scope")
            ungranted_scopes = [
                scope for scope in requested_scopes if scope not in granted_scopes
            ]
            if len(ungranted_scopes) > 0:
                await self.logger.log(
                    action="AuthenticateWithGoogle",
                    entity="User",
                    level="warning",
                    code=403,
                    message="User did not grant all requested scopes for Google authentication",
                    details={"ungranted_scopes": ungranted_scopes},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message=f"Please grant all requested permissions: {', '.join(scope.replace('https://www.googleapis.com/auth/', '') for scope in ungranted_scopes)}.",
                )
            user_info = token.get("userinfo")
            if not user_info:
                await self.logger.log(
                    action="AuthenticateWithGoogle",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to retrieve user info from Google token",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving user information from Google, please try again.",
                )
            google_user_details = {
                "google_id": user_info.get("sub"),
                "google_name": user_info.get("name"),
                "google_email": user_info.get("email"),
                "google_avatar": user_info.get("picture"),
                "google_refresh_token": FernetHandler.encrypt(
                    token.get("refresh_token") or ""
                ),
            }
            if user_id:
                user_response = await self.user_repository.find_one(User.id == user_id)
                if not user_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=user_response.code,
                        data=None,
                        message=user_response.message,
                    )
                user = user_response.data
                if not user:
                    await self.logger.log(
                        action="AuthenticateWithGoogle",
                        entity="User",
                        level="warning",
                        code=404,
                        message="Logged in user not found for Google account change",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Logged in user not found, please log in again.",
                    )
                user.google_id = google_user_details.get("google_id")
                user.google_name = google_user_details.get("google_name")
                user.google_email = google_user_details.get("google_email")
                user.google_avatar = google_user_details.get("google_avatar")
                user.google_refresh_token = google_user_details.get(
                    "google_refresh_token"
                )
                update_user_response = await self.user_repository.update(
                    user,
                    [
                        "google_id",
                        "google_name",
                        "google_email",
                        "google_avatar",
                        "google_refresh_token",
                    ],
                )
                if not update_user_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=update_user_response.code,
                        data=None,
                        message=update_user_response.message,
                    )
                updated_user = update_user_response.data
                if not updated_user:
                    await self.logger.log(
                        action="AuthenticateWithGoogle",
                        entity="User",
                        level="error",
                        code=500,
                        message="Failed to update logged in user's Google account details",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating your Google account information, please try again.",
                    )
                response = UserLoginResponseDto(
                    redirect_url=(redirect_url or "")
                    + f"/user/settings/profile?success=Successfully%20changed%20your%20Google%20account.",
                )
                return BaseResponseDto(success=True, code=200, data=response)
            user_response = await self.user_repository.find_one(
                User.google_id == google_user_details.get("google_id")
            )
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                )
            user = user_response.data
            if user:
                response = await self._login(
                    google_id=str(google_user_details.get("google_id")),
                    google_refresh_token=str(
                        google_user_details.get("google_refresh_token")
                    ),
                    redirect_url=(redirect_url or "") + "/user",
                )
                return response
            encoded_google_user_details_response = JWTHandler.encode_jwt(
                payload=google_user_details,
                secret_key=os.environ.get("GOOGLE_TOKEN_SECRET_KEY"),
                algorithm="HS256",
            )
            if not encoded_google_user_details_response.success:
                await self.logger.log(
                    action="AuthenticateWithGoogle",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to encode Google user details into JWT",
                    details={"error": encoded_google_user_details_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while processing Google user information, please try again.",
                )
            encoded_google_user_details = encoded_google_user_details_response.data
            if not encoded_google_user_details:
                await self.logger.log(
                    action="AuthenticateWithGoogle",
                    entity="User",
                    level="error",
                    code=500,
                    message="Encoded Google user details are None after JWT encoding",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while processing Google user information, please try again.",
                )
            google_token_str = StringHandler.generate_random_string(
                User.GoogleToken.TOKEN_LENGTH
            )
            google_token = Token(
                token=google_token_str,
                token_type=Token.TokenType.GOOGLE_TOKEN["value"],
                expires_at=TimezoneHandler.add_hours(User.GoogleToken.EXPIRE_HOURS),
                details={"token": encoded_google_user_details},
                is_valid=True,
            )
            create_google_token_response = await self.token_repository.create(
                google_token
            )
            if not create_google_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_google_token_response.code,
                    data=None,
                    message=create_google_token_response.message,
                )
            created_google_token = create_google_token_response.data
            if not created_google_token:
                await self.logger.log(
                    action="AuthenticateWithGoogle",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to create Google token for new user authentication",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while processing Google authentication, please try again.",
                )
            redirect_url = (
                (redirect_url or "")
                + f"/login-success?state={oauth_state}&token={google_token_str}___{int(timedelta(hours=User.GoogleToken.EXPIRE_HOURS).total_seconds())}"
            )
            response = UserLoginResponseDto(
                token=google_token_str,
                redirect_url=redirect_url,
            )
            return BaseResponseDto(success=True, code=200, data=response)
        except Exception as ex:
            await self.logger.log(
                action="AuthenticateWithGoogle",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while authenticating with Google",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while authenticating with Google",
            )

    async def logout(self):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success or not user_response.data:
                return BaseResponseDto(
                    success=True,
                    code=200,
                    data=True,
                    message="Successfully logged out",
                )

            user = user_response.data
            invalidate_token_response = await self._invalidate_current_token(
                user.refresh_token
            )
            if not invalidate_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=invalidate_token_response.code,
                    data=False,
                    message=invalidate_token_response.message,
                )

            user.refresh_token = None
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
                message="Successfully logged out",
            )
        except Exception as ex:
            await self.logger.log(
                action="Logout",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while logging out",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while logging out",
            )

    async def get_token_details(self, token):
        try:
            token_response = await self.token_repository.find_one(
                and_(
                    Token.token == FernetHandler.decrypt(token),
                    Token.expires_at > TimezoneHandler.now("UTC"),
                )
            )
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=None,
                    message=token_response.message,
                )
            token = token_response.data
            if not token:
                await self.logger.log(
                    action="GetTokenDetails",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Token not found or expired",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Token not found or expired, please request a new one.",
                )
            token_details = token.details
            if not token_details:
                await self.logger.log(
                    action="GetTokenDetails",
                    entity="User",
                    level="error",
                    code=500,
                    message="Token details are missing",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving token details, please try again.",
                )
            encoded_user_data = token_details.get("user")
            if not encoded_user_data:
                await self.logger.log(
                    action="GetTokenDetails",
                    entity="User",
                    level="error",
                    code=500,
                    message="User data is missing in token details",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving token details, please try again.",
                )
            user_data_response = JWTHandler.decode_jwt(
                token=encoded_user_data,
                secret_key=os.environ.get("USER_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            if not user_data_response.success:
                await self.logger.log(
                    action="GetTokenDetails",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to decode user data from token",
                    details={"error": user_data_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving token details, please try again.",
                )
            user_data = user_data_response.data
            if not user_data:
                await self.logger.log(
                    action="GetTokenDetails",
                    entity="User",
                    level="error",
                    code=500,
                    message="Decoded user data is None after JWT decoding",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving token details, please try again.",
                )
            response = UserTokenDetailsResponseDto(
                name=user_data.get("name") or "",
                email=user_data.get("email") or "",
            )
            return BaseResponseDto(success=True, code=200, data=response)
        except Exception as ex:
            await self.logger.log(
                action="GetTokenDetails",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while retrieving token details",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while retrieving token details, please try again.",
            )

    async def resend_token(self, token):
        try:
            token_response = await self.token_repository.find_one(
                and_(
                    Token.token == FernetHandler.decrypt(token),
                    Token.expires_at > TimezoneHandler.now("UTC"),
                )
            )
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=None,
                    message=token_response.message,
                )
            token = token_response.data
            if not token:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Token not found or expired",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Token not found or expired, please request a new one.",
                )
            token.token = StringHandler.generate_random_number(Token.SHORT_LENGTH)
            token.expires_at = TimezoneHandler.add_hours(Token.EXPIRE_HOURS)
            update_token_response = await self.token_repository.update(
                token, ["token", "expires_at"]
            )
            if not update_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_token_response.code,
                    data=None,
                    message=update_token_response.message,
                )
            updated_token = update_token_response.data
            if not updated_token:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to update token for resending",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while resending token, please try again.",
                )
            token_details = updated_token.details
            if not token_details:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Token details are missing for resending",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while resending token, please try again.",
                )
            encoded_user_data = token_details.get("user")
            if not encoded_user_data:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="User data is missing in token details for resending",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while resending token, please try again.",
                )
            user_data_response = JWTHandler.decode_jwt(
                token=encoded_user_data,
                secret_key=os.environ.get("USER_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            if not user_data_response.success:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Failed to decode user data from token for resending",
                    details={"error": user_data_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while resending token, please try again.",
                )
            user_data = user_data_response.data
            if not user_data:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Decoded user data is None after JWT decoding for resending",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while resending token, please try again.",
                )
            user_email = user_data.get("email")
            if not user_email:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="User email is missing in decoded data for resending",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while resending token, please try again.",
                )
            message = f"Please use the following code to verify your email: {updated_token.token}. This code will expire in {Token.EXPIRE_HOURS} hour{f's' if Token.EXPIRE_HOURS > 1 else ''}."
            email_response = await self.helper_service.send_email(
                to_email=user_email,
                subject="CU Portal - Email Verification Code",
                body=message,
            )
            if not email_response.success:
                await self.logger.log(
                    action="ResendToken",
                    entity="User",
                    level="error",
                    code=email_response.code or 500,
                    message="Failed to send verification email",
                    details={"error": email_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=email_response.code or 500,
                    data=None,
                    message="An error occurred while resending token, please try again.",
                )
            await self.logger.log(
                action="ResendToken",
                entity="User",
                level="info",
                code=200,
                message="Verification email sent successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=UserResendTokenResponseDto(token=FernetHandler.encrypt(updated_token.token)),
                message="Verification email sent successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="ResendToken",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while resending token",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while resending token, please try again.",
            )

    async def refresh_token(self):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                )
            user = user_response.data
            if not user or not user.refresh_token:
                await self.logger.log(
                    action="RefreshToken",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user or refresh token not found for token refresh",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Refresh token not found, please log in again.",
                )

            token_response = await self.token_repository.find_one(
                and_(
                    Token.token == user.refresh_token,
                    Token.token_type == Token.TokenType.REFRESH_TOKEN["value"],
                    Token.expires_at > TimezoneHandler.now("UTC"),
                    Token.is_valid.is_(True),
                )
            )
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=None,
                    message=token_response.message,
                )

            token_record = token_response.data
            if not token_record:
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="Refresh token not found or expired, please log in again.",
                )

            token_record.expires_at = TimezoneHandler.add_days(User.RefreshToken.EXPIRE_DAYS)
            update_token_response = await self.token_repository.update(
                token_record, ["expires_at"]
            )
            if not update_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_token_response.code,
                    data=None,
                    message=update_token_response.message,
                )

            await self.logger.log(
                action="RefreshToken",
                entity="User",
                level="info",
                code=200,
                message="User refresh token expiration extended successfully",
                source="UserService",
            )
            response_data = UserLoginResponseDto(
                user=user, token=user.refresh_token
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=response_data,
                message="Token refreshed successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="RefreshToken",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while refreshing token",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while refreshing token, please try again.",
            )

    async def get_google_stored_token(self, google_details_token):
        try:
            token_response = await self.token_repository.find_one(
                and_(
                    Token.token == google_details_token,
                    Token.token_type == Token.TokenType.GOOGLE_TOKEN["value"],
                    Token.expires_at > TimezoneHandler.now("UTC"),
                )
            )
            if not token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=token_response.code,
                    data=None,
                    message=token_response.message,
                )
            token = token_response.data
            if not token:
                await self.logger.log(
                    action="GetGoogleStoredToken",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Google stored token not found or expired",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Google stored token not found or expired, please try again.",
                )
            google_token_details = token.details
            if not google_token_details:
                await self.logger.log(
                    action="GetGoogleStoredToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Google token details are missing",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving Google stored token, please try again.",
                )
            encoded_google_user_data = google_token_details.get("token")
            if not encoded_google_user_data:
                await self.logger.log(
                    action="GetGoogleStoredToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Encoded Google user data is missing in token details",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving Google stored token, please try again.",
                )
            google_user_data_response = JWTHandler.decode_jwt(
                token=encoded_google_user_data,
                secret_key=os.environ.get("GOOGLE_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            if not google_user_data_response.success:
                await self.logger.log(
                    action="GetGoogleStoredToken",
                    entity="User",
                    level="error",
                    code=google_user_data_response.code or 500,
                    message="Failed to decode Google user data from token",
                    details={"error": google_user_data_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=google_user_data_response.code,
                    data=None,
                    message=google_user_data_response.message,
                )
            google_user_data = google_user_data_response.data
            if not google_user_data:
                await self.logger.log(
                    action="GetGoogleStoredToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Decoded Google user data is None after JWT decoding",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving Google stored token, please try again.",
                )
            access_token_response = await self.helper_service.get_google_access_token(
                google_user_data.get("google_refresh_token") or ""
            )
            if not access_token_response.success:
                await self.logger.log(
                    action="GetGoogleStoredToken",
                    entity="User",
                    level="error",
                    code=access_token_response.code or 500,
                    message="Failed to retrieve Google access token using refresh token",
                    details={"error": access_token_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=access_token_response.code,
                    data=None,
                    message=access_token_response.message,
                )
            access_token = access_token_response.data
            if not access_token:
                await self.logger.log(
                    action="GetGoogleStoredToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Google access token is None after retrieval",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving Google stored token, please try again.",
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=access_token,
                message="Google stored token retrieved successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetGoogleStoredToken",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while retrieving Google stored token",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while retrieving Google stored token, please try again.",
            )

    async def get_google_access_token(self):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="GetGoogleAccessToken",
                    entity="User",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged in user for getting Google access token",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="GetGoogleAccessToken",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found for getting Google access token",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found, please log in again.",
                )
            access_token_response = await self.helper_service.get_google_access_token(
                logged_in_user.google_refresh_token
            )
            if not access_token_response.success:
                await self.logger.log(
                    action="GetGoogleAccessToken",
                    entity="User",
                    level="error",
                    code=access_token_response.code or 500,
                    message="Failed to retrieve Google access token using refresh token",
                    details={"error": access_token_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=access_token_response.code,
                    data=None,
                    message=access_token_response.message,
                )
            access_token = access_token_response.data
            if not access_token:
                await self.logger.log(
                    action="GetGoogleAccessToken",
                    entity="User",
                    level="error",
                    code=500,
                    message="Google access token is None after retrieval",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving Google access token, please try again.",
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=access_token,
                message="Google access token retrieved successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetGoogleAccessToken",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while retrieving Google access token",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while retrieving Google access token, please try again.",
            )

    async def get_statistics(self, data):
        try:
            response = await self.user_repository.execute_stored_function(
                "get_user_statistics",
                {
                    "p_faculty_id": data.faculty_id,
                    "p_department_id": data.department_id,
                    "p_year_id": data.year_id,
                },
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                )
            statistics_data = response.data
            if not statistics_data:
                await self.logger.log(
                    action="GetStatistics",
                    entity="User",
                    level="warning",
                    code=404,
                    message="No statistics data found for the given criteria",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="No statistics data found for the given criteria.",
                )
            statistics_data = cast(UserStatisticsResponseDto, statistics_data)
            return BaseResponseDto(
                success=True,
                code=200,
                data=statistics_data,
                message="User statistics retrieved successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetStatistics",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while getting user statistics",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while getting user statistics, please try again.",
            )

    async def update_many(self, data):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="UpdateMany",
                    entity="User",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged in user for updating users",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=False,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="UpdateMany",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found for updating users",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="Logged in user not found, please log in again.",
                )
            logged_in_user_permissions = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions.success:
                await self.logger.log(
                    action="UpdateMany",
                    entity="User",
                    level="error",
                    code=logged_in_user_permissions.code or 500,
                    message=f"Failed to retrieve logged in user permissions for updating users",
                    details={"error": logged_in_user_permissions.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_permissions.code,
                    data=False,
                    message=logged_in_user_permissions.message,
                )
            logged_in_user_permissions = logged_in_user_permissions.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="UpdateMany",
                    entity="User",
                    level="error",
                    code=500,
                    message=f"Logged in user permissions are None after retrieval for updating users",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=False,
                    message="An error occurred while retrieving your permissions, please try again.",
                )
            if "Assign Roles" not in logged_in_user_permissions:
                await self.logger.log(
                    action="UpdateMany",
                    entity="User",
                    level="warning",
                    code=403,
                    message=f"Logged in user does not have 'Assign Roles' permission to update user roles",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=False,
                    message=f"You do not have the 'Assign Roles' permission required to update user roles.",
                )
            for record in data.data_to_update:
                dynamic_includes = self.helper_service.generate_dynamic_includes(
                    User, ["pending_user.attachment", "attachment"]
                )
                user_response = await self.user_repository.find_one(
                    User.id == record.id, dynamic_includes
                )
                if not user_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=user_response.code,
                        data=False,
                        message=user_response.message,
                    )
                user = user_response.data
                if not user:
                    await self.logger.log(
                        action="UpdateMany",
                        entity="User",
                        level="warning",
                        code=404,
                        message=f"User with ID {record.id} not found for updating",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"User with ID {record.id} not found.",
                    )
                if user.id == logged_in_user.id:
                    await self.logger.log(
                        action="UpdateMany",
                        entity="User",
                        level="warning",
                        code=403,
                        message=f"User with ID {user.id} attempted to update their own record, which is not allowed",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=403,
                        data=False,
                        message=f"You are not allowed to update your own user record through this endpoint.",
                    )
                if user.status and (
                    not record.role_id or record.role_id == user.role_id
                ):
                    await self.logger.log(
                        action="UpdateMany",
                        entity="User",
                        level="warning",
                        code=400,
                        message=f"User with ID {user.id} has already been approved, and their status cannot be updated again",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message=f"User with ID {user.id} has already been approved, and their status cannot be updated again.",
                    )
                if not user.status and not user.pending_user:
                    await self.logger.log(
                        action="UpdateMany",
                        entity="User",
                        level="warning",
                        code=400,
                        message=f"User with ID {user.id} is suspended not pending approval, and their status cannot be updated",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message=f"User with ID {user.id} is suspended not pending approval, and their status cannot be updated.",
                    )
                user.status = record.approved if not user.status else user.status
                if record.role_id:
                    dynamic_includes = self.helper_service.generate_dynamic_includes(
                        Role, ["role_links.exact_role"]
                    )
                    role_response = await self.role_repository.find_one(
                        Role.id == record.role_id, dynamic_includes
                    )
                    if not role_response.success:
                        return BaseResponseDto(
                            success=False,
                            code=role_response.code,
                            data=False,
                            message=role_response.message,
                        )
                    role = role_response.data
                    if not role:
                        await self.logger.log(
                            action="UpdateMany",
                            entity="Role",
                            level="warning",
                            code=404,
                            message=f"Role with ID {record.role_id} not found for updating user with ID {user.id}",
                            source="UserService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=404,
                            data=False,
                            message=f"Role with ID {record.role_id} not found.",
                        )
                    role_permissions = [perm.name for perm in role.exact_roles]
                    if not set(role_permissions).issubset(
                        set(logged_in_user_permissions)
                    ):
                        await self.logger.log(
                            action="UpdateMany",
                            entity="User",
                            level="warning",
                            code=403,
                            message=f"Logged in user does not have sufficient permissions to assign role with ID {record.role_id} to user with ID {user.id}",
                            source="UserService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=403,
                            data=False,
                            message=f"You do not have sufficient permissions to assign the role specified for user with ID {user.id}.",
                        )
                    user.role = role
                if user.pending_user:
                    attachment = user.pending_user.attachment
                    delete_pending_user_response = (
                        await self.pending_user_repository.delete(user.pending_user)
                    )
                    if not delete_pending_user_response.success:
                        return BaseResponseDto(
                            success=False,
                            code=delete_pending_user_response.code,
                            data=False,
                            message=delete_pending_user_response.message,
                        )
                    if attachment:
                        await self.helper_service.delete_attachment(
                            attachment=attachment
                        )
                if not user.status:
                    attachment = user.attachment
                    delete_user_response = await self.user_repository.delete(user)
                    if not delete_user_response.success:
                        return BaseResponseDto(
                            success=False,
                            code=delete_user_response.code,
                            data=False,
                            message=delete_user_response.message,
                        )
                    if attachment:
                        await self.helper_service.delete_attachment(
                            attachment=attachment
                        )
                else:
                    update_user_response = await self.user_repository.update(
                        user, ["status", "role_id"]
                    )
                    if not update_user_response.success:
                        return BaseResponseDto(
                            success=False,
                            code=update_user_response.code,
                            data=False,
                            message=update_user_response.message,
                        )
            await self.logger.log(
                action="UpdateMany",
                entity="User",
                level="info",
                code=200,
                message="Multiple users updated successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Users updated successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="UpdateMany",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while updating multiple users",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating users, please try again.",
            )

    async def suspend(self, user_id):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="SuspendUser",
                    entity="User",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged in user for suspending user",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="SuspendUser",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found for suspending user",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found, please log in again.",
                )
            if logged_in_user.id == user_id:
                await self.logger.log(
                    action="SuspendUser",
                    entity="User",
                    level="warning",
                    code=403,
                    message=f"User with ID {logged_in_user.id} attempted to suspend their own account, which is not allowed",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message=f"You are not allowed to suspend your own account.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="SuspendUser",
                    entity="User",
                    level="error",
                    code=logged_in_user_permissions_response.code or 500,
                    message=f"Failed to retrieve logged in user permissions for suspending user with ID {user_id}",
                    details={"error": logged_in_user_permissions_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_permissions_response.code,
                    data=None,
                    message=logged_in_user_permissions_response.message,
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="SuspendUser",
                    entity="User",
                    level="error",
                    code=500,
                    message=f"Logged in user permissions are None after retrieval for suspending user with ID {user_id}",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving your permissions, please try again.",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                User, ["role.role_links.exact_role"]
            )
            user_response = await self.user_repository.find_one(
                User.id == user_id, dynamic_includes
            )
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="SuspendUser",
                    entity="User",
                    level="warning",
                    code=404,
                    message=f"User with ID {user_id} not found for suspension",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"User not found.",
                )
            user_permissions = (
                [perm.name for perm in user.role.exact_roles]
                if user.role and user.role.exact_roles
                else []
            )
            if not set(user_permissions).issubset(set(logged_in_user_permissions)):
                await self.logger.log(
                    action="SuspendUser",
                    entity="User",
                    level="warning",
                    code=403,
                    message=f"Logged in user does not have sufficient permissions to suspend user with ID {user_id}",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message=f"You do not have sufficient permissions to suspend this user.",
                )
            if not user.status:
                await self.logger.log(
                    action="SuspendUser",
                    entity="User",
                    level="warning",
                    code=400,
                    message=f"User with ID {user_id} is not active and cannot be suspended",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"User must be active to be suspended.",
                )
            user.status = False
            update_user_response = await self.user_repository.update(user, ["status"])
            if not update_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_user_response.code,
                    data=None,
                    message=update_user_response.message,
                )
            message = f"""
            Dear {user.name}\n\n
            Your account has been suspended. If you believe this is a mistake or have any questions, please contact our support team for assistance.\n\n
            Thank you for your understanding.\n\n
            """
            email_response = await self.helper_service.send_email(
                to_email=user.email,
                subject="CU - Portal - Account Suspension Notification",
                body=message,
            )
            if not email_response.success:
                await self.logger.log(
                    action="SuspendUser",
                    entity="User",
                    level="error",
                    code=email_response.code or 500,
                    message=f"Failed to send suspension notification email to user with ID {user_id}",
                    details={"error": email_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=email_response.code,
                    data=None,
                    message=email_response.message,
                )
            await self.logger.log(
                action="SuspendUser",
                entity="User",
                level="info",
                code=200,
                message=f"User with ID {user_id} suspended successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message=f"User suspended successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="SuspendUser",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while suspending user with ID {user_id}",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message=f"An error occurred while suspending user, please try again.",
            )

    async def unsuspend(self, user_id):
        try:
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="UnsuspendUser",
                    entity="User",
                    level="error",
                    code=logged_in_user_permissions_response.code or 500,
                    message=f"Failed to retrieve logged in user permissions for unsuspending user with ID {user_id}",
                    details={"error": logged_in_user_permissions_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_permissions_response.code,
                    data=None,
                    message=logged_in_user_permissions_response.message,
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="UnsuspendUser",
                    entity="User",
                    level="error",
                    code=500,
                    message=f"Logged in user permissions are None after retrieval for unsuspending user with ID {user_id}",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while retrieving your permissions, please try again.",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                User, ["pending_user", "role.role_links.exact_role"]
            )
            user_response = await self.user_repository.find_one(
                User.id == user_id, dynamic_includes
            )
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="UnsuspendUser",
                    entity="User",
                    level="warning",
                    code=404,
                    message=f"User with ID {user_id} not found for unsuspension",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"User not found.",
                )
            user_permissions = (
                [perm.name for perm in user.role.exact_roles]
                if user.role and user.role.exact_roles
                else []
            )
            if not set(user_permissions).issubset(set(logged_in_user_permissions)):
                await self.logger.log(
                    action="UnsuspendUser",
                    entity="User",
                    level="warning",
                    code=403,
                    message=f"Logged in user does not have sufficient permissions to unsuspend user with ID {user_id}",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message=f"You do not have sufficient permissions to unsuspend this user.",
                )
            if user.status:
                await self.logger.log(
                    action="UnsuspendUser",
                    entity="User",
                    level="warning",
                    code=400,
                    message=f"User with ID {user_id} is already active and cannot be unsuspended",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"User must be suspended to be unsuspended.",
                )
            if user.pending_user:
                await self.logger.log(
                    action="UnsuspendUser",
                    entity="User",
                    level="warning",
                    code=400,
                    message=f"User with ID {user_id} is pending approval and cannot be unsuspended",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"User is pending approval and cannot be unsuspended.",
                )
            user.status = True
            update_user_response = await self.user_repository.update(user, ["status"])
            if not update_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_user_response.code,
                    data=None,
                    message=update_user_response.message,
                )
            message = f"""
            Dear {user.name}\n\n
            Your account has been unsuspended. You can now access your account and resume using our services. If you have any questions or need assistance, please feel free to reach out to our support team.\n\n
            Thank you for your understanding.\n\n
            """
            email_response = await self.helper_service.send_email(
                to_email=user.email,
                subject="CU - Portal - Account Unsuspension Notification",
                body=message,
            )
            if not email_response.success:
                await self.logger.log(
                    action="UnsuspendUser",
                    entity="User",
                    level="error",
                    code=email_response.code or 500,
                    message=f"Failed to send unsuspension notification email to user with ID {user_id}",
                    details={"error": email_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=email_response.code,
                    data=None,
                    message=email_response.message,
                )
            await self.logger.log(
                action="UnsuspendUser",
                entity="User",
                level="info",
                code=200,
                message=f"User with ID {user_id} unsuspended successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message=f"User unsuspended successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="UnsuspendUser",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while unsuspending user with ID {user_id}",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message=f"An error occurred while unsuspending user, please try again.",
            )

    async def update_academic_data(self, data):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="UpdateAcademicData",
                    entity="User",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged in user for updating academic data",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=False,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="UpdateAcademicData",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found for updating academic data",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="Logged in user not found, please log in again.",
                )
            verify_academic_data_response = (
                await self.helper_service.verify_academic_data(
                    faculty_id=data.faculty_id,
                    department_id=data.department_id,
                    year_id=data.year_id,
                )
            )
            if not verify_academic_data_response.success:
                await self.logger.log(
                    action="UpdateAcademicData",
                    entity="User",
                    level="error",
                    code=verify_academic_data_response.code or 500,
                    message=f"Failed to verify academic data for updating user : {verify_academic_data_response.message}",
                    details={"error": verify_academic_data_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=verify_academic_data_response.code,
                    data=False,
                    message=verify_academic_data_response.message,
                )
            logged_in_user.faculty_id = data.faculty_id
            logged_in_user.department_id = data.department_id
            logged_in_user.year_id = data.year_id
            logged_in_user.study_type = data.study_type
            update_user_response = await self.user_repository.update(
                logged_in_user, ["faculty_id", "department_id", "year_id", "study_type"]
            )
            if not update_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_user_response.code,
                    data=False,
                    message=update_user_response.message,
                )
            await self.logger.log(
                action="UpdateAcademicData",
                entity="User",
                level="info",
                code=200,
                message="User academic data updated successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Academic data updated successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="UpdateAcademicData",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while updating user academic data",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating academic data, please try again.",
            )

    async def get_current_user(self, includes=None):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="GetCurrentUser",
                    entity="User",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged in user",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="GetCurrentUser",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found, please log in again.",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                User, includes
            )
            user_response = await self.user_repository.find_one(
                User.id == logged_in_user.id, dynamic_includes
            )
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="GetCurrentUser",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found in database",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found in database, please log in again.",
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=user,
                message="Logged in user retrieved successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetCurrentUser",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while getting current user",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while getting current user, please try again.",
            )

    async def get_current_user_id(self):
        try:
            current_user_response = await self.get_current_user()
            if not current_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=current_user_response.code,
                    data=None,
                    message=current_user_response.message,
                )
            current_user = current_user_response.data
            if not current_user:
                await self.logger.log(
                    action="GetCurrentUserId",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found when getting current user ID",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found, please log in again.",
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=current_user.id,
                message="Current user ID retrieved successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetCurrentUserId",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while getting current user ID",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while getting current user ID, please try again.",
            )

    async def get_user_permissions(self):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="GetUserPermissions",
                    entity="User",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged in user for getting permissions",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="GetUserPermissions",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found for getting permissions",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found, please log in again.",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Role, ["role_links.exact_role"]
            )
            role_response = await self.role_repository.find_one(
                Role.id == logged_in_user.role_id, dynamic_includes
            )
            if not role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=role_response.code,
                    data=None,
                    message=role_response.message,
                )
            role = role_response.data
            if not role:
                await self.logger.log(
                    action="GetUserPermissions",
                    entity="Role",
                    level="warning",
                    code=404,
                    message=f"Role with ID {logged_in_user.role_id} not found for getting permissions of user with ID {logged_in_user.id}",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Role not found for the logged in user, please contact support.",
                )
            permissions = [perm.name for perm in role.exact_roles]
            return BaseResponseDto(
                success=True,
                code=200,
                data=permissions,
                message="User permissions retrieved successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetUserPermissions",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while getting user permissions",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while getting user permissions, please try again.",
            )

    async def has_permissions(self, data):
        try:
            user_permissions_response = await self.get_user_permissions()
            if not user_permissions_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_permissions_response.code,
                    data=None,
                    message=user_permissions_response.message,
                )
            user_permissions = user_permissions_response.data
            if not user_permissions:
                await self.logger.log(
                    action="HasPermissions",
                    entity="User",
                    level="warning",
                    code=404,
                    message="Logged in user not found for checking permissions",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found, please log in again.",
                )
            if data.is_and:
                has_perms = all(
                    perm in user_permissions for perm in data.required_permissions
                )
            else:
                has_perms = any(
                    perm in user_permissions for perm in data.required_permissions
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=has_perms,
                message="Permission check completed successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="HasPermissions",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while checking user permissions",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while checking permissions, please try again.",
            )

    async def register_device(self, device_id, device_token):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="RegisterDevice",
                    entity="Device",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged in user for registering device",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )

            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="RegisterDevice",
                    entity="Device",
                    level="warning",
                    code=404,
                    message="Logged in user not found for registering device",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found, please log in again.",
                )

            device_response = await self.device_repository.find_one(
                Device.device_id == device_id
            )
            if not device_response.success:
                return BaseResponseDto(
                    success=False,
                    code=device_response.code,
                    data=None,
                    message=device_response.message,
                )

            device = device_response.data
            if device:
                device.user_id = logged_in_user.id
                device.device_token = device_token
                update_response = await self.device_repository.update(
                    device, ["user_id", "device_token"]
                )
                if not update_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=update_response.code,
                        data=None,
                        message=update_response.message,
                    )
            else:
                create_response = await self.device_repository.create(
                    Device(
                        device_id=device_id,
                        user_id=logged_in_user.id,
                        device_token=device_token,
                    )
                )
                if not create_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=create_response.code,
                        data=None,
                        message=create_response.message,
                    )

            await self.logger.log(
                action="RegisterDevice",
                entity="Device",
                level="info",
                code=200,
                message="Device registered successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Device registered successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="RegisterDevice",
                entity="Device",
                level="error",
                code=500,
                message="An error occurred while registering device",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while registering device, please try again.",
            )

    async def unregister_device(self, device_id):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="UnregisterDevice",
                    entity="Device",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged in user for unregistering device",
                    details={"error": logged_in_user_response.error},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )

            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged in user not found, please log in again.",
                )

            device_response = await self.device_repository.find_one(
                (Device.device_id == device_id)
            )
            if not device_response.success:
                return BaseResponseDto(
                    success=False,
                    code=device_response.code,
                    data=None,
                    message=device_response.message,
                )

            device = device_response.data
            if not device:
                return BaseResponseDto(
                    success=True,
                    code=200,
                    data=True,
                    message="Device unregistered successfully.",
                )
            if device.user_id != logged_in_user.id:
                await self.logger.log(
                    action="UnregisterDevice",
                    entity="Device",
                    level="warning",
                    code=403,
                    message=f"Logged in user does not own device with ID {device_id} and cannot unregister it",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message=f"You do not have permission to unregister this device.",
                )
            delete_response = await self.device_repository.delete(device)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )

            await self.logger.log(
                action="UnregisterDevice",
                entity="Device",
                level="info",
                code=200,
                message="Device unregistered successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Device unregistered successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="UnregisterDevice",
                entity="Device",
                level="error",
                code=500,
                message="An error occurred while unregistering device",
                details={"error": repr(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while unregistering device, please try again.",
            )

