from abc import ABC, abstractmethod
from typing import Coroutine
from fastapi import Request, Response


class IDeletableController(ABC):
    @abstractmethod
    def delete(self, request: Request) -> Coroutine[None, None, Response]:
        pass
