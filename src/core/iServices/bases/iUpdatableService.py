from abc import abstractmethod
from typing import TypeVar, Generic, Any, Coroutine
from core.dtos.baseResponseDto import BaseResponseDto
from core.iServices.bases.iBaseService import IBaseService

T = TypeVar("T")  # Entity Type


class IUpdatableService(Generic[T], IBaseService):
    @abstractmethod
    def update(
        self, data: T
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[T | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass
