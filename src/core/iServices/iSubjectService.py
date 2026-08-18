from abc import abstractmethod
from core.iServices.bases.iCrudService import ICrudService
from core.entities.subject import Subject
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userSubjectLinkDtos import (UserSubjectLinkRegisterDto, UserSubjectLinkUnregisterDto)
from core.dtos.subjectDtos import (SubjectAvailableSearchDto,SubjectSearchDto)


class ISubjectService(
    ICrudService[Subject]
):
   
    @abstractmethod
    async def register(self, data:UserSubjectLinkRegisterDto) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def unregister(self, data:UserSubjectLinkUnregisterDto) -> BaseResponseDto[bool]:
        pass

    @abstractmethod
    async def get_enrolled(self) -> BaseResponseDto[list[Subject]]:
        pass

    @abstractmethod
    async def get_available(self, data: SubjectAvailableSearchDto) -> BaseResponseDto[list[Subject]]:
        pass

    @abstractmethod
    async def get_enrolled_one(self, data: SubjectSearchDto) -> BaseResponseDto[Subject]:
        pass