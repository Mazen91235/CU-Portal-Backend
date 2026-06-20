from abc import abstractmethod
from typing import TypeVar, Generic
from core.dtos.baseDtos import BaseResponseDto
from core.iServices.bases.iBaseService import IBaseService

T = TypeVar("T")  # Entity Type


class ICreatableService(Generic[T], IBaseService):
    @abstractmethod
    async def create(self, data: T) -> BaseResponseDto[T]:
        pass
