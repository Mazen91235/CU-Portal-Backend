from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iCrudController import ICrudController

class ISubjectController(ICrudController):
  # Additional Query Functions
    @abstractmethod
    async def search(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def register(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def unregister(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_enrolled(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_available(self, request: Request) -> Response:
        pass
    
    @abstractmethod
    async def get_enrolled_one(self, request: Request) -> Response:
        pass