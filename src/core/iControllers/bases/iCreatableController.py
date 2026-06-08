from abc import ABC, abstractmethod
from typing import Coroutine
from fastapi import Request, Response


class ICreatableController(ABC):
    @abstractmethod
    def create(self, request: Request) -> Coroutine[None, None, Response]:
        pass
