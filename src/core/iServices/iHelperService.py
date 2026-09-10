from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, Type
from core.entities.user import User
from core.entities.notification import Notification
from core.entities.attachment import Attachment
from core.dtos.baseDtos import BaseResponseDto
from core.models.fileModels import FetchedModel, DownloadedFileModel, FileModel

T = TypeVar("T")  # Entity Type
U = TypeVar("U")  # EntitySearchDto Type


class IHelperService(ABC, Generic[U]):
    @abstractmethod
    async def get_ip_address(
        self,
    ) -> BaseResponseDto[str]:
        pass

    @abstractmethod
    async def get_logged_in_user(
        self,
    ) -> BaseResponseDto[User]:
        pass

    @abstractmethod
    async def get_logged_in_user_permissions(
        self,
    ) -> BaseResponseDto[set[str]]:
        pass

    @abstractmethod
    async def verify_restricted_access(
        self,
        faculty_id: int | None = None,
        department_id: int | None = None,
        year_id: int | None = None,
        subject_id: int | None = None,
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def verify_academic_data(
        self,
        faculty_id: int | None = None,
        department_id: int | None = None,
        year_id: int | None = None,
        subject_id: int | None = None,
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def send_email(
        self, to_email: str, subject: str, body: str
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    def generate_dynamic_includes(
        self, cls: Type[T], includes: list[str] | None
    ) -> list[Any]:
        pass

    @abstractmethod
    def generate_dynamic_selects(
        self, entity_name: str, selects: list[str] | None
    ) -> list[Any]:
        pass

    @abstractmethod
    def generate_dynamic_order_by(
        self, entity_name: str, order_by: list[str] | None
    ) -> list[Any]:
        pass

    @abstractmethod
    def generate_dynamic_predicate(
        self,
        cls: Type[T],
        data: U,
        query_fields: list[str] | None,
        is_and: bool,
        starts_with: bool,
        is_exact: bool,
        allow_nulls: bool = False,
    ) -> Any:
        pass

    # Notification Functions
    @abstractmethod
    async def send_notification(
        self,
        notification_type: Notification.NotificationType,
        parent_id: int,
        content: str,
        url: str | None = None,
        faculty_id: int | None = None,
        department_id: int | None = None,
        year_id: int | None = None,
        subject_id: int | None = None,
    ) -> BaseResponseDto[bool]:
        pass

    # File Functions
    @abstractmethod
    def get_file_id_from_url(
        self,
        url: str,
    ) -> str | None:
        pass

    @abstractmethod
    def get_file_url_from_id(
        self,
        file_id: str,
    ) -> str | None:
        pass

    @abstractmethod
    def get_file_type(
        self,
        mime_type: str,
    ) -> str:
        pass

    @abstractmethod
    def verify_file_type(
        self,
        mime_type: str,
        expected_type: str,
    ) -> bool:
        pass

    @abstractmethod
    def verify_file_size(
        self,
        file_size: str,
        max_size_in_bytes: int,
    ) -> bool:
        pass

    @abstractmethod
    async def verify_file_exists_on_drive(
        self,
        url: str,
    ) -> BaseResponseDto[FileModel]:
        pass

    @abstractmethod
    async def remove_files_from_drive(self, files: list[dict]) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def fetch_from_drive(
        self,
        file_id: str,
        visited: set[str] | None = None,
        max_retries: int = 6,
    ) -> BaseResponseDto[FetchedModel]:
        pass

    @abstractmethod
    async def get_google_access_token(
        self,
        user_refresh_token: str,
        max_retries: int = 6,
    ) -> BaseResponseDto[str]:
        pass

    @abstractmethod
    async def download_file_from_drive(
        self,
        file_id: str,
        max_retries: int = 6,
    ) -> BaseResponseDto[DownloadedFileModel]:
        pass

    @abstractmethod
    async def set_file_public_on_drive(
        self,
        access_token: str,
        file_id: str,
        max_retries: int = 6,
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def upload_file_to_drive(
        self,
        access_token: str,
        name: str,
        content: bytes,
        size: str | None = None,
        max_retries: int = 6,
    ) -> BaseResponseDto[FileModel]:
        pass

    @abstractmethod
    async def delete_file_from_drive(
        self,
        access_token: str,
        file_id: str,
        max_retries: int = 6,
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def copy_file_on_drive(
        self,
        access_token: str,
        file_id: str,
        new_name: str | None = None,
        max_retries: int = 6,
    ) -> BaseResponseDto[FileModel]:
        pass

    # Attachment Functions
    @abstractmethod
    async def create_attachment(
        self,
        is_file: bool,
        url: str,
        author_id: int,
        source_name: str,
        source_id: int,
        link_title: str | None = None,
        fetched: bool | None = None,
    ) -> BaseResponseDto[Attachment]:
        pass

    @abstractmethod
    async def delete_attachment(
        self,
        attachment_id: int | None = None,
        attachment: Attachment | None = None,
    ) -> BaseResponseDto:
        pass
