from abc import abstractmethod
from typing import Coroutine
from fastapi import Request, Response
from core.iControllers.bases.iCrudController import ICrudController


class IUserController(ICrudController):
    @abstractmethod
    def verify_email(self, request: Request) -> Coroutine[None, None, Response]:
        pass

    @abstractmethod
    def login(self, request: Request) -> Coroutine[None, None, Response]:
        pass

    @abstractmethod
    def logout(self, request: Request) -> Coroutine[None, None, Response]:
        pass

    @abstractmethod
    def forget_password(self, request: Request) -> Coroutine[None, None, Response]:
        pass

    @abstractmethod
    def reset_password(self, request: Request) -> Coroutine[None, None, Response]:
        pass

    @abstractmethod
    def change_password(self, request: Request) -> Coroutine[None, None, Response]:
        pass

    @abstractmethod
    def resend_token(self, request: Request) -> Coroutine[None, None, Response]:
        pass
