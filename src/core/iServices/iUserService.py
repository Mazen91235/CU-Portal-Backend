from abc import abstractmethod
from typing import Any, Coroutine
from core.dtos.baseDtos import BaseResponseDto
from core.iServices.bases.iCrudService import ICrudService
from core.entities.user import User
from core.dtos.userDtos import UserSearchDto, UserLoginResponseDto


class IUserService(ICrudService[User, UserSearchDto]):
    @abstractmethod
    def verify_email(self, token: str) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def login(
        self, email: str, password: str
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[UserLoginResponseDto | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def logout(self) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def forget_password(self, email: str) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def reset_password(
        self, token: str, new_password: str
    ) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def change_password(
        self, old_password: str, new_password: str
    ) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def resend_token(self, email: str) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass
