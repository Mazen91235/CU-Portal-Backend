from abc import ABC, abstractmethod
from fastapi import Request, Response


class IMaterialController(ABC):
    @abstractmethod
    async def create(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def update(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_by_id(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_detail(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_parents(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def delete_many(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def copy_many(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def move_many(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def fetch_one_material_from_drive(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def fetch_materials_from_drive(self, request: Request) -> Response:
        pass
