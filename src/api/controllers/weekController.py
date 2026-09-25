from typing import cast
from core.iControllers.iWeekController import IWeekController
from core.iServices.iWeekService import IWeekService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.entities.week import Week
from core.dtos.weekDtos import (
    WeekCreateDto,
    WeekUpdateDto,
    WeekSearchDto,
    WeekResponseDto,
)
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler


class WeekController(IWeekController):
    def __init__(self, week_service: IWeekService, logger: IBaseLogger):
        self.week_service = week_service
        self.logger = logger

    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[WeekSearchDto].generate(
                WeekSearchDto, {"id": id}
            )
            response = await self.week_service.find_one(
                entity_search_dto,
                ["faculty", "department", "year", "materials"],
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            week = response.data
            if not week:
                await self.logger.log(
                    action="FindOne",
                    entity="Week",
                    level="info",
                    code=404,
                    message="Week not found",
                    source="WeekController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Week not found",
                )
            week_mapped = Mapper[Week, WeekResponseDto].map(week, WeekResponseDto, True)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=week_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="WeekController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[WeekSearchDto].generate_from_query(
                WeekSearchDto, query
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

            response = await self.week_service.find(
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

            weeks = response.data
            weeks_mapped = Mapper[Week, WeekResponseDto].map_list(
                weeks or [], WeekResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=weeks_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="WeekController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            week = Mapper[WeekCreateDto, Week].map(data, Week)
            response = await self.week_service.create(week)
            if not response.success:
                await self.week_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            week_mapped = Mapper[Week, WeekResponseDto].map(
                response.data, WeekResponseDto, True
            )
            await self.week_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=week_mapped,
            )
        except Exception as e:
            await self.week_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="WeekController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, id, data):
        try:
            week = cast(Week, Mapper[WeekUpdateDto, Week].map(data, Week))
            week.id = id
            response = await self.week_service.update(week)
            if not response.success:
                await self.week_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            week_mapped = Mapper[Week, WeekResponseDto].map(
                response.data, WeekResponseDto, True
            )
            await self.week_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=week_mapped,
            )
        except Exception as e:
            await self.week_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="WeekController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            week = Generator[Week].generate(Week, {"id": id})
            response = await self.week_service.delete(week)
            if not response.success:
                await self.week_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.week_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Week deleted successfully",
            )
        except Exception as e:
            await self.week_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="WeekController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
