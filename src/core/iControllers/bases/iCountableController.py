from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from fastapi import Request, Response
from core.models.queryModel import QueryModel

U = TypeVar("U")  # EntitySearchDto


class ICountableController(ABC, Generic[U]):
    @abstractmethod
    async def count(self, request: Request, query: QueryModel[U]) -> Response:
        pass
