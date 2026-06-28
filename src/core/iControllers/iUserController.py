from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController


class IUserController(IQueryableController, ICreatableController, IUpdatableController):
    # Additional Query Functions
    @abstractmethod
    async def search(self, request: Request) -> Response:
        pass

    # Auth Functions
    @abstractmethod
    async def verify_email(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def login_with_google(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def google_authentication_redirect(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def is_logged_in(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def logout(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_token_details(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def resend_token(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_google_stored_token(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_google_access_token(self, request: Request) -> Response:
        pass

    # User Functions
    @abstractmethod
    async def get_statistics(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def update_many(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def update_academic_data(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_current_user(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_user_permissions(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def has_permissions(self, request: Request) -> Response:
        pass
