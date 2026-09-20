from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from core.dtos.baseDtos import BaseResponseDto

T = TypeVar("T")


class IBaseRepository(ABC, Generic[T]):
    @abstractmethod
    async def find_one(
        self,
        predicate: Any = None,
        includes: List[Any] = [],
        selects: List[Any] = [],
        order_by: List[Any] = [],
        session: AsyncSession | None = None,
    ) -> BaseResponseDto[T]:
        pass

    @abstractmethod
    async def find(
        self,
        predicate: Any = None,
        includes: List[Any] = [],
        selects: List[Any] = [],
        order_by: List[Any] = [],
        page: int = 1,
        limit: int = 50,
        session: AsyncSession | None = None,
    ) -> BaseResponseDto[List[T]]:
        pass

    @abstractmethod
    async def count(
        self, predicate: Any = None, session: AsyncSession | None = None
    ) -> BaseResponseDto[int]:
        pass

    @abstractmethod
    async def find_distinct(
        self,
        predicate: Any = None,
        column: Any = None,
        session: AsyncSession | None = None,
    ) -> BaseResponseDto[List[Any]]:
        pass

    @abstractmethod
    async def create(
        self, entity: T, session: AsyncSession | None = None
    ) -> BaseResponseDto[T]:
        pass

    @abstractmethod
    async def update(
        self, entity: T, updates: List[str] = [], session: AsyncSession | None = None
    ) -> BaseResponseDto[T]:
        pass

    @abstractmethod
    async def delete(
        self, entity: T, session: AsyncSession | None = None
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def execute_sql(
        self, command: str, params: dict = {}, session: AsyncSession | None = None
    ) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def execute_stored_function(
        self, function_name: str, params: dict = {}, session: AsyncSession | None = None
    ) -> BaseResponseDto[Any]:
        pass

    @abstractmethod
    async def begin_transaction(self, session: AsyncSession | None = None) -> None:
        pass

    @abstractmethod
    async def commit_transaction(self, session: AsyncSession | None = None) -> None:
        pass

    @abstractmethod
    async def rollback_transaction(self, session: AsyncSession | None = None) -> None:
        pass
