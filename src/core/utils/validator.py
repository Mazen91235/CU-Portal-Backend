from email_validator import validate_email, EmailNotValidError
from core.dtos.baseDtos import BaseResponseDto


class Validator:
    ALLOWED_DOMAINS = [
        "cu.edu.eg",
        "stud.cu.edu.eg",
    ]

    ALLOWED_FILE_TYPES = [
        "image",
        "pdf",
        "doc",
        "sheet",
        "ppt",
        "video",
        "audio",
        "text",
        "archive",
        "gdrive",
    ]

    @staticmethod
    def validate_email(email: str, return_validated: bool = False) -> BaseResponseDto:
        try:
            validated = validate_email(email, check_deliverability=True)
            if return_validated:
                return BaseResponseDto(success=True, code=200, data=validated)
            return BaseResponseDto(
                success=True, code=200, data=validated.normalized.lower()
            )
        except EmailNotValidError as ex:
            return BaseResponseDto(
                success=False,
                code=400,
                data="",
                message="Invalid email address provided",
                error=str(ex),
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data="",
                message="An error occurred while validating the email address.",
                error=str(ex),
            )

    @staticmethod
    def is_valid_phone_number(phone_number: str) -> bool:
        if not phone_number:
            return False
        if "+" in phone_number and phone_number[0] != "+":
            return False
        had_code = True if phone_number.startswith("+") else False
        phone_number = phone_number.replace("+", "")
        if not phone_number.isdigit():
            return False
        if len(phone_number) < 10 or len(phone_number) > 12:
            return False
        if len(phone_number) != 11 and not had_code:
            return False
        if len(phone_number) == 11 and phone_number[0] != "0":
            return False
        if len(phone_number) < 12 and had_code:
            return False
        if len(phone_number) == 12 and phone_number[0:2] != "20":
            return False
        return True

    @staticmethod
    def is_allowed_domain(domain: str) -> bool:
        return any(domain.endswith(allowed) for allowed in Validator.ALLOWED_DOMAINS)

    @staticmethod
    def is_allowed_file_type(
        file_type: str, excluded_types: list[str] | None = None
    ) -> bool:
        return any(
            file_type.startswith(allowed)
            for allowed in Validator.ALLOWED_FILE_TYPES
            if not excluded_types or allowed not in excluded_types
        )
