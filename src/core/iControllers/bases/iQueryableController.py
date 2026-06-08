from abc import ABC, abstractmethod
from typing import Coroutine
from fastapi import Request, Response


class IQueryableController(ABC):
    @abstractmethod
    def find_one(self, request: Request) -> Coroutine[None, None, Response]:
        pass

    @abstractmethod
    def find(self, request: Request) -> Coroutine[None, None, Response]:
        pass
