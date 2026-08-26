from abc import abstractmethod
from fastapi import Request, Response
from core.iControllers.bases.iCountableController import ICountableController
from core.iControllers.bases.iQueryableController import IQueryableController
from core.dtos.logDtos import LogSearchDto


class ILogController(
    ICountableController[LogSearchDto],
    IQueryableController[LogSearchDto],
):
    @abstractmethod
    async def delete(self, request: Request, logs_count: int) -> Response:
        pass

    @abstractmethod
    async def get_log_actions(self, request: Request) -> Response:
        pass

    @abstractmethod
    async def get_log_entities(self, request: Request) -> Response:
        pass
