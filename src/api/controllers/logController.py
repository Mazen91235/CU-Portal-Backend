from typing import cast
from core.iControllers.iLogController import ILogController
from core.iServices.iLogService import ILogService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.log import Log
from core.dtos.logDtos import (
    LogResponseDto,
    LogSearchDto,
)
from core.models.queryModel import QueryModel


class LogController(ILogController):
    def __init__(self, log_service: ILogService, logger: IBaseLogger):
        self.log_service = log_service
        self.logger = logger

    # CRUD Functions
    async def count(self, request, query):
        try:
            entity_search_dto = Generator[LogSearchDto].generate_from_query(
                LogSearchDto, query
            )
            is_and = query.is_and
            starts_with = query.starts_with
            is_exact = query.is_exact

            response = await self.log_service.count(
                entity_search_dto, is_and, starts_with, is_exact
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            log_count = response.data
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=log_count,
            )
        except Exception as e:
            await self.logger.log(
                action="Count",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="LogController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[LogSearchDto].generate(
                LogSearchDto, {"id": id}
            )
            response = await self.log_service.find_one(entity_search_dto, ["user"])
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            log = response.data
            if not log:
                await self.logger.log(
                    action="FindOne",
                    entity="Log",
                    level="info",
                    code=404,
                    message="Log not found",
                    source="LogController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Log not found",
                )
            log_mapped = Mapper[Log, LogResponseDto].map(log, LogResponseDto, True)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=log_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="LogController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[LogSearchDto].generate_from_query(
                LogSearchDto, query
            )
            includes = query.includes
            selects = query.selects
            is_and = query.is_and
            starts_with = query.starts_with
            is_exact = query.is_exact
            order_by = query.order_by
            descending = query.descending
            page = query.page or 1
            limit = query.limit or 50

            response = await self.log_service.find(
                entity_search_dto,
                includes,
                selects,
                is_and,
                starts_with,
                is_exact,
                order_by,
                descending,
                page,
                limit,
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            logs = response.data
            logs_mapped = Mapper[Log, LogResponseDto].map_list(
                logs or [], LogResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=logs_mapped,
                next_page=response.next_page,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="LogController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, logs_count):
        try:
            await self.log_service.begin_transaction()
            response = await self.log_service.delete(logs_count)
            if not response.success:
                await self.log_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            response_data = response.data
            if not response_data:
                await self.log_service.rollback_transaction()
                await self.logger.log(
                    action="Delete",
                    entity="Log",
                    level="info",
                    code=404,
                    message="No logs found to delete",
                    source="LogController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="No logs found to delete",
                )
            await self.log_service.commit_transaction()
            await self.logger.log(
                action="Delete",
                entity="Log",
                level="info",
                code=200,
                message=f"Successfully deleted {logs_count} logs",
                source="LogController",
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=True,
            )
        except Exception as e:
            await self.log_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="LogController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_log_actions(self, request):
        try:
            response = await self.log_service.get_log_actions()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            log_actions = response.data
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=log_actions,
            )
        except Exception as e:
            await self.logger.log(
                action="GetLogActions",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="LogController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_log_entities(self, request):
        try:
            response = await self.log_service.get_log_entities()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            log_entities = response.data
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=log_entities,
            )
        except Exception as e:
            await self.logger.log(
                action="GetLogEntities",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="LogController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
