from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Any, Coroutine
from core.dtos.baseResponseDto import BaseResponseDto

T = TypeVar("T")


class IBaseRepository(ABC, Generic[T]):
    @abstractmethod
    def find_one(
        self,
        predicate: Any = None,
        includes: List[Any] = [],
        selects: List[Any] = [],
        order_by: list[Any] = [],
        descending: bool = False,
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[T | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def find(
        self,
        predicate: Any = None,
        includes: List[Any] = [],
        selects: List[Any] = [],
        order_by: list[Any] = [],
        descending: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> Coroutine[Any, Any, BaseResponseDto[List[T]]]:
        pass

    @abstractmethod
    def count(
        self, predicate: Any = None
    ) -> Coroutine[Any, Any, BaseResponseDto[int]]:
        pass

    @abstractmethod
    def create(
        self, entity: T
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[T | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def update(
        self, entity: T, updates: List[str] = []
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[T | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def delete(self, entity: T) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def execute_sql(
        self, command: str, params: dict = {}
    ) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass

    @abstractmethod
    def begin_transaction(self) -> Coroutine[Any, Any, None]:
        pass

    @abstractmethod
    def commit_transaction(self) -> Coroutine[Any, Any, None]:
        pass

    @abstractmethod
    def rollback_transaction(self) -> Coroutine[Any, Any, None]:
        pass
