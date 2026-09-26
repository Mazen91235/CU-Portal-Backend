import re
import os
from dotenv import load_dotenv
from email_validator import validate_email, EmailNotValidError
from core.dtos.baseDtos import BaseResponseDto

load_dotenv()  # Load environment variables from .env file


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

    ALLOWED_TYPES = ["file", "folder", "youtube", "drive", "external"]

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
                error=repr(ex),
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data="",
                message="An error occurred while validating the email address.",
                error=repr(ex),
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

    @staticmethod
    def is_allowed_type(type: str) -> bool:
        return type in Validator.ALLOWED_TYPES

    @staticmethod
    def is_valid_youtube_url(url: str) -> bool:
        youtube_regex = r"^(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com|youtubeeducation\.com)/.*$"
        return re.match(youtube_regex, url) is not None

    @staticmethod
    def is_valid_drive_url(url: str) -> bool:
        drive_regex = r"^(https?://)?(www\.)?(drive\.google\.com|docs\.google\.com|forms\.google\.com|slides\.google\.com|sheets\.google\.com|sites\.google\.com)/.*$"
        return re.match(drive_regex, url) is not None

    @staticmethod
    def is_valid_external_url(url: str) -> bool:
        external_regex = re.compile(
            r"^(https?://)"  # http:// or https://
            r"(([A-Za-z0-9-]+\.)+[A-Za-z]{2,6})"  # Domain name only
            r"(/[A-Za-z0-9\-._~:/?#[\]@!$&\'()*+,;=]*)?$"  # Path and query string
        )
        return re.match(external_regex, url) is not None

    @staticmethod
    def is_valid_url_based_on_type(url: str, type: str) -> bool:
        if type == "youtube":
            return Validator.is_valid_youtube_url(url)
        elif type == "drive" or type == "file":
            return Validator.is_valid_drive_url(url)
        elif type == "external":
            return Validator.is_valid_external_url(url)
        else:
            return False

    @staticmethod
    def is_int(value: str) -> bool:
        try:
            int(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_number(value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_hostname_is_background_worker(hostname: str) -> bool:
        if os.environ.get("HOSTED", "false").lower() == "true":
            return True
        return (
            "onrender" in hostname.lower()
            or "bg-worker" in hostname.lower()
            or "localhost" in hostname.lower()
        )
