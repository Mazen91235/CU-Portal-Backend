from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iCrudController import ICrudController
from core.dtos.subjectDtos import (
    SubjectCreateDto,
    SubjectUpdateDto,
    SubjectSearchDto,
    SubjectSearchAvailableDto,
)
from core.dtos.userSubjectLinkDtos import UserSubjectLinkActionDto
from core.models.queryModel import QueryModel


class ISubjectController(
    ICrudController[SubjectCreateDto, SubjectUpdateDto, SubjectSearchDto]
):
    @abstractmethod
    async def get_available(
        self, request: Request, query: QueryModel[SubjectSearchAvailableDto]
    ) -> Response:
        pass

    @abstractmethod
    async def get_enrolled(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_enrolled_one(self, request: Request, id: int) -> Response:
        pass

    @abstractmethod
    async def register(
        self, request: Request, data: UserSubjectLinkActionDto
    ) -> Response:
        pass

    @abstractmethod
    async def unregister(
        self, request: Request, data: UserSubjectLinkActionDto
    ) -> Response:
        pass
