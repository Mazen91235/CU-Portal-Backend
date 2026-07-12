from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iQueryableController import IQueryableController
from core.iControllers.bases.iCreatableController import ICreatableController
from core.iControllers.bases.iUpdatableController import IUpdatableController
from core.iControllers.bases.iDeletableController import IDeletableController


class IExamController(
    IQueryableController, 
    ICreatableController, 
    IUpdatableController,
    IDeletableController
):
    # Admin Controllers
    @abstractmethod
    async def create_exam(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def update_exam(self, request: Request, exam_id: int) -> Response:
        pass

    @abstractmethod
    async def delete_exam(self, request: Request, exam_id: int) -> Response:
        pass

    @abstractmethod
    async def get_exams_admin(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_exam_admin(self, request: Request, exam_id: int) -> Response:
        pass

    # User Controllers
    @abstractmethod
    async def get_exams_user(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_exam_user(self, request: Request, exam_id: int) -> Response:
        pass