from abc import ABC, abstractmethod
from typing import Coroutine
from fastapi import Request, Response


class IUpdatableController(ABC):
    @abstractmethod
    def update(self, request: Request) -> Coroutine[None, None, Response]:
        pass
