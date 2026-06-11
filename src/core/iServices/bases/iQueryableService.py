from abc import abstractmethod
from typing import TypeVar, Generic, Any, Coroutine
from core.dtos.baseDtos import BaseResponseDto
from core.iServices.bases.iBaseService import IBaseService

T = TypeVar("T")  # Entity Type
U = TypeVar("U")  # EntitySearchDto Type


class IQueryableService(Generic[T, U], IBaseService):
    @abstractmethod
    def find_one(
        self,
        data: U | None = None,
        includes: list[str] = [],
        selects: list[str] = [],
        is_and: bool = False,
        starts_with: bool = True,
        is_exact: bool = True,
        order_by: list[str] = [],
        descending: bool = False,
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[T | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def find(
        self,
        data: U | None = None,
        includes: list[str] = [],
        selects: list[str] = [],
        is_and: bool = False,
        starts_with: bool = True,
        is_exact: bool = True,
        order_by: list[str] = [],
        descending: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[list[T] | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass
