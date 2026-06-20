import os
from typing import cast
from sqlalchemy.orm import selectinload
from sqlalchemy import and_
from core.iServices.iUserService import IUserService
from core.entities.user import User
from core.entities.pendingUser import PendingUser
from core.entities.role import Role
from core.dtos.userDtos import (
    UserLoginResponseDto,
)
from core.dtos.baseDtos import BaseResponseDto
from core.iRepositories.iBaseRepository import IBaseRepository
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iServices.iHelperService import IHelperService
from core.entities.token import Token
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.fernetHandler import FernetHandler
from core.utils.stringHandler import StringHandler
from core.utils.validator import Validator
from core.utils.jwtHandler import JWTHandler


class UserService(IUserService):
    def __init__(
        self,
        user_repository: IBaseRepository[User],
        token_repository: IBaseRepository[Token],
        role_repository: IBaseRepository[Role],
        pending_user_repository: IBaseRepository[PendingUser],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.user_repository = user_repository
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
        includes=[],
        selects=[],
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=[],
        descending=False,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                User, data, is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                User, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "User", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "User", order_by
            )
            result = await self.user_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                    error=result.error,
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
                details={"error": str(ex)},
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
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                User, data, is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                User, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "User", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "User", order_by
            )
            result = await self.user_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
                page,
                limit,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                    error=result.error,
                )
            users = result.data
            return BaseResponseDto(success=True, data=users)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred while finding users",
                details={"error": str(ex)},
                source="UserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding users",
                error=str(ex),
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
                    Token.type == Token.TokenType.GOOGLE_TOKEN,
                    Token.expires_at > TimezoneHandler.now("UTC"),
                )
            )
            if not google_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=google_token_response.code,
                    data=None,
                    message=google_token_response.message,
                    error=google_token_response.error,
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
            google_token.expire_at = TimezoneHandler.add_hours(-1)
            update_google_token_response = await self.token_repository.update(
                google_token, ["expire_at"]
            )
            if not update_google_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_google_token_response.code,
                    data=None,
                    message=update_google_token_response.message,
                    error=update_google_token_response.error,
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
                    code=400,
                    message="Failed to decode Google token details",
                    details={"error": google_user_details_response.message},
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Bad Request, Please try authorizing with Google again",
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
                    code=400,
                    message="Invalid email address provided",
                    details={"error": validate_email_response.message},
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
                if not data.url:
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
                url = data.url
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
                        code=400,
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
            email_exists_response = await self.user_repository.find_one(
                User.email == data.email
            )
            if not email_exists_response.success:
                return BaseResponseDto(
                    success=False,
                    code=email_exists_response.code,
                    data=None,
                    message=email_exists_response.message,
                    error=email_exists_response.error,
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
                    error=phone_exists_response.error,
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
            json_user_data = data.model_dump()
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
                type=Token.TokenType.EMAIL_VERIFICATION,
                expires_at=expires_at,
            )
            created_token_response = await self.token_repository.create(token)
            if not created_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=created_token_response.code,
                    data=None,
                    message=created_token_response.message,
                    error=created_token_response.error,
                )
            created_token = created_token_response.data
            message = f"Please use the following code to verify your email: {token_str}. This code will expire in {User.VerificationToken.EXPIRE_HOURS} hour({f"s" if User.VerificationToken.EXPIRE_HOURS > 1 else ''})."
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
            return BaseResponseDto(success=True, code=201, data=None)
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
            user_response = await self.user_repository.find_one(User.id == data.id)
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
                    level="warning",
                    code=404,
                    message="User not found with this ID",
                    source="UserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="User not found",
                )
            avatar = user.details.get("avatar", user.google_avatar)
            should_remove = None
            if data.url and data.url != avatar:
                file_id = self.helper_service.get_file_id_from_url(data.url)
                if not file_id:
                    await self.logger.log(
                        action="Update",
                        entity="User",
                        level="warning",
                        code=400,
                        message="Invalid file URL provided for avatar",
                        source="UserService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid file uploaded for avatar, please try again with a valid file.",
                    )
                file_response = await self.helper_service.fetch_from_drive(file_id)
                if not file_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="User",
                        level="warning",
                        code=400,
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
                        action="Update",
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
                        action="Update",
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
                        message="Only image files are allowed for the avatar.",
                    )
                if not self.helper_service.verify_file_size(
                    file.data.size, User.MAX_ALLOWED_FILE_SIZE_B
                ):
                    await self.logger.log(
                        action="Update",
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
                should_remove = avatar
            data.details["avatar"] = data.url
            update_user_response = await self.user_repository.update(
                data, ["name", "details"]
            )
            if not update_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_user_response.code,
                    data=None,
                    message=update_user_response.message,
                    error=update_user_response.error,
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
            while should_remove:
                file_id = self.helper_service.get_file_id_from_url(should_remove)
                should_remove = None
                if file_id:
                    access_token_response = (
                        await self.helper_service.get_google_access_token(
                            user.google_refresh_token or ""
                        )
                    )
                    if (
                        not access_token_response.success
                        or not access_token_response.data
                    ):
                        break
                    access_token = access_token_response.data
                    remove_file_response = (
                        await self.helper_service.delete_file_from_drive(
                            access_token, file_id
                        )
                    )
                    if (
                        not remove_file_response.success
                        or not remove_file_response.data
                    ):
                        await self.logger.log(
                            action="Update",
                            entity="User",
                            level="warning",
                            code=400,
                            message="Failed to remove old avatar from Google Drive",
                            details={"error": remove_file_response.error},
                            source="UserService",
                        )
                        break
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
            if not tokens:
                await self.logger.log(
                    action="InvalidateTokens",
                    entity="User",
                    level="info",
                    code=200,
                    message="No tokens found for the user to invalidate",
                    source="UserService",
                )
                return BaseResponseDto(success=True, data=True)
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
                    code=400,
                    message="Failed to decode user data from token",
                    details={"error": decoded_user_data_response.message},
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
            token.expire_at = TimezoneHandler.add_hours(-1)
            update_token_response = await self.token_repository.update(
                token, ["expire_at"]
            )
            if not update_token_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_token_response.code,
                    data=False,
                    message=update_token_response.message,
                    error=update_token_response.error,
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
                    error=user_role_response.error,
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
            )
            create_user_response = await self.user_repository.create(user)
            if not create_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_user_response.code,
                    data=False,
                    message=create_user_response.message,
                    error=create_user_response.error,
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
            if token_details.get("pending_approval"):
                pending_user = PendingUser(
                    user_id=created_user.id,
                    url=token_details.get("pending_approval"),
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
                        error=create_pending_user_response.error,
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

    async def login(self, google_id, google_refresh_token):
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
                    error=user_response.error,
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
                    message="User not found, please verify your email first.",
                )
            refresh_token = StringHandler.generate_random_string(Token.LONG_LENGTH)
            expires_at = TimezoneHandler.add_days(Token.REFRESH_TOKEN_EXPIRE_DAYS)
            user.refresh_token = refresh_token
            user.refresh_expire_at = expires_at
            user.google_refresh_token = FernetHandler.encrypt(google_refresh_token)
            update_user_response = await self.user_repository.update(
                user, ["refresh_token", "refresh_expire_at", "google_refresh_token"]
            )
            if not update_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_user_response.code,
                    data=None,
                    message=update_user_response.message,
                    error=update_user_response.error,
                )
            await self.logger.log(
                action="Login",
                entity="User",
                level="info",
                code=200,
                message="User logged in successfully",
                source="UserService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=UserLoginResponseDto(user=user, token=refresh_token),
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
