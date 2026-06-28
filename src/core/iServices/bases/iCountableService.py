from abc import abstractmethod
from typing import TypeVar, Generic
from core.iServices.bases.iBaseService import IBaseService
from core.dtos.baseDtos import BaseResponseDto

U = TypeVar("U")  # EntitySearchDto Type


class ICountableService(Generic[U], IBaseService):
    @abstractmethod
    async def count(
        self,
        data: U | None = None,
        is_and: bool = False,
        starts_with: bool = True,
        is_exact: bool = True,
    ) -> BaseResponseDto[int]:
        pass
