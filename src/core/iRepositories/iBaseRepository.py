from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Any, Coroutine
from core.dtos.baseDtos import BaseResponseDto

T = TypeVar("T")


class IBaseRepository(ABC, Generic[T]):
    @abstractmethod
    async def find_one(
        self,
        predicate: Any = None,
        includes: List[Any] = [],
        selects: List[Any] = [],
        order_by: list[Any] = [],
        descending: bool = False,
    ) -> BaseResponseDto[T]:
        pass

    @abstractmethod
    async def find(
        self,
        predicate: Any = None,
        includes: List[Any] = [],
        selects: List[Any] = [],
        order_by: list[Any] = [],
        descending: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> BaseResponseDto[List[T]]:
        pass

    @abstractmethod
    async def count(self, predicate: Any = None) -> BaseResponseDto[int]:
        pass

    @abstractmethod
    async def create(self, entity: T) -> BaseResponseDto[T]:
        pass

    @abstractmethod
    async def update(self, entity: T, updates: List[str] = []) -> BaseResponseDto[T]:
        pass

    @abstractmethod
    async def delete(self, entity: T) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def execute_sql(
        self, command: str, params: dict = {}
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def begin_transaction(self) -> None:
        pass

    @abstractmethod
    async def commit_transaction(self) -> None:
        pass

    @abstractmethod
    async def rollback_transaction(self) -> None:
        pass
