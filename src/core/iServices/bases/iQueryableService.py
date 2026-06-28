from abc import abstractmethod
from typing import TypeVar, Generic
from core.iServices.bases.iBaseService import IBaseService
from core.dtos.baseDtos import BaseResponseDto

T = TypeVar("T")  # Entity Type
U = TypeVar("U")  # EntitySearchDto Type


class IQueryableService(Generic[T, U], IBaseService):
    @abstractmethod
    async def find_one(
        self,
        data: U | None = None,
        includes: list[str] | None = None,
        selects: list[str] | None = None,
        is_and: bool = False,
        starts_with: bool = True,
        is_exact: bool = True,
        order_by: list[str] | None = None,
        descending: bool = False,
    ) -> BaseResponseDto[T]:
        pass

    @abstractmethod
    async def find(
        self,
        data: U | None = None,
        includes: list[str] | None = None,
        selects: list[str] | None = None,
        is_and: bool = False,
        starts_with: bool = True,
        is_exact: bool = True,
        order_by: list[str] | None = None,
        descending: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> BaseResponseDto[list[T]]:
        pass
