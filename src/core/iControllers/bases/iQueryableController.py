from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from fastapi import Request, Response
from core.models.queryModel import QueryModel

U = TypeVar("U")  # EntitySearchDto


class IQueryableController(ABC, Generic[U]):
    @abstractmethod
    async def find_one(self, request: Request, id: int) -> Response:
        pass

    @abstractmethod
    async def find(self, request: Request, query: QueryModel[U]) -> Response:
        pass
