from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.entities.user import User
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userDtos import (
    UserHasPermissionsDto,
    UserSearchDto,
    UserSignUpResponseDto,
    UserLoginWithGoogleResponseDto,
    UserLoginResponseDto,
    UserStatisticsResponseDto,
    UserTokenDetailsResponseDto,
    UserResendTokenResponseDto,
    UserUpdateAcademicDataDto,
    UserUpdateUsersDto,
)


class IUserService(
    IQueryableService[User, UserSearchDto],
    IUpdatableService[User],
):
    @abstractmethod
    async def create(self, data: User) -> BaseResponseDto[UserSignUpResponseDto]:
        pass

    @abstractmethod
    async def verify_email(self, token: str) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def login_with_google(self) -> BaseResponseDto[UserLoginWithGoogleResponseDto]:
        pass

    @abstractmethod
    async def authenticate_with_google(self) -> BaseResponseDto[UserLoginResponseDto]:
        pass

    @abstractmethod
    async def logout(self) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def get_token_details(
        self, token: str
    ) -> BaseResponseDto[UserTokenDetailsResponseDto]:
        pass

    @abstractmethod
    async def resend_token(self, token: str) -> BaseResponseDto[UserResendTokenResponseDto]:
        pass

    @abstractmethod
    async def refresh_token(self) -> BaseResponseDto[UserLoginResponseDto]:
        pass

    @abstractmethod
    async def get_google_stored_token(
        self, google_details_token: str
    ) -> BaseResponseDto[str]:
        pass

    @abstractmethod
    async def get_google_access_token(self) -> BaseResponseDto[str]:
        pass

    @abstractmethod
    async def get_statistics(
        self, data: UserSearchDto
    ) -> BaseResponseDto[UserStatisticsResponseDto]:
        pass

    @abstractmethod
    async def update_many(self, data: UserUpdateUsersDto) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def update_academic_data(
        self, data: UserUpdateAcademicDataDto
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def get_current_user(
        self, includes: list[str] | None = None
    ) -> BaseResponseDto[User]:
        pass

    @abstractmethod
    async def get_current_user_id(self) -> BaseResponseDto[int]:
        pass

    @abstractmethod
    async def get_user_permissions(self) -> BaseResponseDto[list[str]]:
        pass

    @abstractmethod
    async def has_permissions(
        self, data: UserHasPermissionsDto
    ) -> BaseResponseDto[bool]:
        pass
