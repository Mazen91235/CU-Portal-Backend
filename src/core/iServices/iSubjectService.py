from abc import abstractmethod
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.iServices.bases.iDeletableService import IDeletableService
from core.entities.subject import Subject
from core.dtos.baseDtos import BaseResponseDto
#from core.dtos.subjectDtos import (
   
#)


class ISubjectService(
    IQueryableService[Subject],
    IUpdatableService[Subject],
    IDeletableService[Subject]
):
    @abstractmethod
    async def create(self, data: Subject) -> BaseResponseDto:
        pass

    @abstractmethod
    async def search(
        self,
        user,
        query: str | None = None,
        faculty_id: int | None = None,
        department_id: int | None = None,
        year_id: int | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> BaseResponseDto:
        pass

    @abstractmethod
    async def register(self, user_id: int, subject_id: int) -> BaseResponseDto:
        pass

    @abstractmethod
    async def unregister(self, user_id: int, subject_id: int) -> BaseResponseDto:
        pass

    @abstractmethod
    async def get_enrolled(self, user_id: int) -> BaseResponseDto:
        pass

    @abstractmethod
    async def get_available(self, user_id: int) -> BaseResponseDto:
        pass

    @abstractmethod
    async def search_registered(
        self, user_id: int, query: str | None = None, page: int = 1, limit: int = 50,
    ) -> BaseResponseDto:
        pass

    @abstractmethod
    async def get_enrolled_one(self, user_id: int, subject_id: int) -> BaseResponseDto:
        pass