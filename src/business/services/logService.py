from sqlalchemy import func
from core.iServices.iLogService import ILogService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.log import Log
from core.dtos.baseDtos import BaseResponseDto


class LogService(ILogService):
    def __init__(
        self,
        log_repository: IBaseRepository[Log],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.log_repository = log_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.log_repository.begin_transaction()

    async def commit_transaction(self):
        await self.log_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.log_repository.rollback_transaction()

    # CRUD Functions
    async def count(
        self,
        data=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                Log,
                data,
                ["action", "entity", "message"],
                is_and,
                starts_with,
                is_exact,
            )
            result = await self.log_repository.count(
                predicate,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            log_count = result.data
            return BaseResponseDto(success=True, data=log_count)
        except Exception as ex:
            await self.logger.log(
                action="Count",
                entity="Log",
                level="error",
                code=500,
                message=f"An error occurred while counting logs",
                details={"error": repr(ex)},
                source="LogService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while counting logs",
            )

    async def find_one(
        self,
        data=None,
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                Log,
                data,
                ["action", "entity", "message"],
                is_and,
                starts_with,
                is_exact,
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Log, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Log", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Log", order_by
            )
            result = await self.log_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                [],
                descending,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            log = result.data
            return BaseResponseDto(success=True, data=log)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while finding log",
                details={"error": repr(ex)},
                source="LogService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding log",
            )

    async def find(
        self,
        data=None,
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
        page=1,
        limit=50,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                Log,
                data,
                ["action", "entity", "message"],
                is_and,
                starts_with,
                is_exact,
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Log, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Log", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Log", order_by
            )
            result = await self.log_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                [],
                descending,
                page,
                limit,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            logs = result.data
            return BaseResponseDto(success=True, data=logs, next_page=result.next_page)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while finding logs",
                details={"error": repr(ex)},
                source="LogService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding logs",
            )

    async def delete(self, logs_count):
        try:
            logs_response = await self.log_repository.find(
                order_by=["created_at"],
                page=1,
                limit=logs_count,
            )
            if not logs_response.success:
                return BaseResponseDto(
                    success=False,
                    code=logs_response.code,
                    data=None,
                    message=logs_response.message,
                )
            logs = logs_response.data
            if not logs:
                await self.logger.log(
                    action="Delete",
                    entity="Log",
                    level="info",
                    code=404,
                    message="No logs found to delete",
                    details={},
                    source="LogService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="No logs found to delete",
                )
            for log in logs:
                delete_response = await self.log_repository.delete(log)
                if not delete_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=delete_response.code,
                        data=None,
                        message=delete_response.message,
                    )
            await self.logger.log(
                action="Delete",
                entity="Log",
                level="info",
                code=200,
                message=f"Successfully deleted {logs_count} logs",
                details={},
                source="LogService",
            )
            return BaseResponseDto(success=True, code=200, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while deleting logs",
                details={"error": repr(ex)},
                source="LogService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting logs",
            )

    # Log Specific Functions
    async def get_log_actions(self):
        try:
            result = await self.log_repository.find_distinct(
                column=Log.action,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            log_actions = result.data
            return BaseResponseDto(success=True, data=log_actions)
        except Exception as ex:
            await self.logger.log(
                action="GetLogActions",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while retrieving log actions",
                details={"error": repr(ex)},
                source="LogService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while retrieving log actions",
            )

    async def get_log_entities(self):
        try:
            result = await self.log_repository.find_distinct(
                column=Log.entity,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            log_entities = result.data
            return BaseResponseDto(success=True, data=log_entities)
        except Exception as ex:
            await self.logger.log(
                action="GetLogEntities",
                entity="Log",
                level="error",
                code=500,
                message="An error occurred while retrieving log entities",
                details={"error": repr(ex)},
                source="LogService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while retrieving log entities",
            )
