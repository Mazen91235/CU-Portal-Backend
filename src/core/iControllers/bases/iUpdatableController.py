from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from fastapi import Request, Response

T = TypeVar("T")  # EntityUpdateDto


class IUpdatableController(ABC, Generic[T]):
    @abstractmethod
    async def update(self, request: Request, id: int, data: T) -> Response:
        pass
