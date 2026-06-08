from abc import abstractmethod
from typing import TypeVar, Generic, Any, Coroutine
from core.dtos.baseResponseDto import BaseResponseDto
from core.iServices.bases.iBaseService import IBaseService

T = TypeVar("T")  # Entity Type


class IDeletableService(Generic[T], IBaseService):
    @abstractmethod
    def delete(self, data: T | None) -> Coroutine[Any, Any, BaseResponseDto[bool]]:
        pass
