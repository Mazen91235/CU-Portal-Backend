from abc import abstractmethod
from typing import Any, Coroutine
from core.dtos.baseDtos import BaseResponseDto
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.entities.user import User
from core.dtos.userDtos import UserSearchDto, UserLoginResponseDto


class IUserService(
    IQueryableService[User, UserSearchDto],
    ICreatableService[User],
    IUpdatableService[User],
):
    @abstractmethod
    def verify_email(self, token: str) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def login(
        self, google_id: str, google_refresh_token: str
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[UserLoginResponseDto | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def logout(self) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def resend_token(self, email: str) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass
