from abc import abstractmethod
from typing import TypeVar, Generic
from core.iServices.bases.iBaseService import IBaseService
from core.dtos.baseDtos import BaseResponseDto

T = TypeVar("T")  # Entity Type


class IDeletableService(Generic[T], IBaseService):
    @abstractmethod
    async def delete(self, data: T | None) -> BaseResponseDto[bool]:
        pass
