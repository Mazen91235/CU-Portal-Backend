from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, Type, Coroutine
from fastapi import UploadFile
from core.entities.user import User
from core.entities.patient import Patient
from core.dtos.baseDtos import BaseResponseDto

T = TypeVar("T")  # Entity Type
U = TypeVar("U")  # EntitySearchDto Type


class IHelperService(ABC, Generic[U]):
    @abstractmethod
    def get_ip_address(
        self,
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[str | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def get_logged_in_user(
        self,
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[User | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def get_logged_in_patient(
        self,
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[Patient | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def store_file(
        self, file: UploadFile
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[str | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def validate_image_file(self, file: UploadFile) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    def resolve_voice_and_image_files(
        self, files: list[UploadFile]
    ) -> BaseResponseDto[tuple[UploadFile, UploadFile] | None]:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def send_email(
        self, to_email: str, subject: str, body: str
    ) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def generate_dynamic_includes(self, cls: Type[T], includes: list[str]) -> list[Any]:
        pass

    @abstractmethod
    def generate_dynamic_selects(
        self, entity_name: str, selects: list[str]
    ) -> list[Any]:
        pass

    @abstractmethod
    def generate_dynamic_order_by(
        self, entity_name: str, order_by: list[str]
    ) -> list[Any]:
        pass

    @abstractmethod
    def generate_dynamic_predicate(
        self,
        cls: Type[T],
        data: U,
        is_and: bool,
        starts_with: bool,
        is_exact: bool,
    ) -> Any:
        pass
