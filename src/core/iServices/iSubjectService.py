from abc import abstractmethod
from core.iServices.bases.iCrudService import ICrudService
from core.entities.subject import Subject
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.subjectDtos import SubjectSearchDto, SubjectSearchAvailableDto


class ISubjectService(ICrudService[Subject, SubjectSearchDto]):
    @abstractmethod
    async def get_available(
        self, data: SubjectSearchAvailableDto
    ) -> BaseResponseDto[list[Subject]]:
        pass

    @abstractmethod
    async def get_enrolled(self) -> BaseResponseDto[list[Subject]]:
        pass

    @abstractmethod
    async def get_enrolled_one(self, subject_id: int) -> BaseResponseDto[Subject]:
        pass

    @abstractmethod
    async def register(self, subject_id: int) -> BaseResponseDto:
        pass

    @abstractmethod
    async def unregister(self, subject_id: int) -> BaseResponseDto:
        pass
