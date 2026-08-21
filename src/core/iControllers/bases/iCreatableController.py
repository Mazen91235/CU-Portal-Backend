from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from fastapi import Request, Response

T = TypeVar("T")  # EntityCreateDto


class ICreatableController(ABC, Generic[T]):
    @abstractmethod
    async def create(self, request: Request, data: T) -> Response:
        pass
