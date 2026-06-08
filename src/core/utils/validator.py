from email_validator import validate_email, EmailNotValidError
from core.dtos.baseResponseDto import BaseResponseDto


class Validator:
    @staticmethod
    def validate_email(email: str) -> BaseResponseDto[str]:
        try:
            validated = validate_email(email, check_deliverability=True)
            return BaseResponseDto(
                success=True, code=200, data=validated.normalized.lower()
            )
        except EmailNotValidError as ex:
            return BaseResponseDto(success=False, code=400, data="", message=str(ex))
        except Exception:
            return BaseResponseDto(
                success=False,
                code=500,
                data="",
                message="An error occurred while validating the email address.",
            )

    @staticmethod
    def validate_password(password: str) -> BaseResponseDto[bool]:
        # Password must be at least 8 characters long and contain a mix of letters, numbers, and special characters
        if len(password) < 8:
            return BaseResponseDto(
                success=False,
                code=400,
                data=False,
                message="Password must be at least 8 characters long",
            )
        if not any(char.isdigit() for char in password):
            return BaseResponseDto(
                success=False,
                code=400,
                data=False,
                message="Password must contain at least one digit",
            )
        if not any(char.isalpha() for char in password):
            return BaseResponseDto(
                success=False,
                code=400,
                data=False,
                message="Password must contain at least one letter",
            )
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/" for char in password):
            return BaseResponseDto(
                success=False,
                code=400,
                data=False,
                message="Password must contain at least one special character",
            )
        return BaseResponseDto(success=True, code=200, data=True)
