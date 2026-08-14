from core.iControllers.iYearController import IYearController
from core.iServices.iYearService import IYearService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.entities.year import Year
from core.dtos.yearDtos import (
    YearCreateDto,
    YearUpdateDto,
    YearSearchDto,
    YearResponseDto,
)
from core.models.queryModel import QueryModel
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser


class YearController(IYearController):
    def __init__(self, year_service: IYearService, logger: IBaseLogger):
        self.year_service = year_service
        self.logger = logger

    async def find_one(self, request):
        try:
            year_id = request.path_params.get("year_id")
            if not year_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Year ID is required",
                )
            entity_search_dto = Generator[YearSearchDto].generate(
                YearSearchDto, {"id": int(year_id)}
            )
            response = await self.year_service.find_one(
                entity_search_dto,
                ["users"],
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            year = response.data
            if not year:
                await self.logger.log(
                    action="FindOne",
                    entity="Year",
                    level="info",
                    code=404,
                    message="Year not found",
                    source="YearController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Year not found",
                )
            year_mapped = Mapper[Year, YearResponseDto].map(year, YearResponseDto, True)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=year_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="YearController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request):
        try:
            query = Parser.parse_query(
                request.query_params.get("query", "{}"),
                QueryModel[YearSearchDto],
            )
            entity_search_dto = Generator[YearSearchDto].generate_from_query(
                YearSearchDto, query
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

            response = await self.year_service.find(
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

            years = response.data
            if not years:
                await self.logger.log(
                    action="Find",
                    entity="Year",
                    level="info",
                    code=404,
                    message="Years not found",
                    source="YearController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Years not found",
                )

            years_mapped = Mapper[Year, YearResponseDto].map_list(
                years, YearResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=years_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="YearController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request):
        try:
            await self.year_service.begin_transaction()
            payload = await request.json()
            data = Generator[YearCreateDto].generate(YearCreateDto, payload)
            year = Mapper[YearCreateDto, Year].map(data, Year)
            response = await self.year_service.create(year)
            if not response.success:
                await self.year_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            year_mapped = Mapper[Year, YearResponseDto].map(
                response.data, YearResponseDto, True
            )
            await self.year_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=year_mapped,
            )
        except Exception as e:
            await self.year_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="YearController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request):
        try:
            await self.year_service.begin_transaction()
            year_id = request.path_params.get("year_id")
            if not year_id:
                await self.year_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Year ID is required",
                )
            payload = await request.json()
            payload["id"] = int(year_id)
            data = Generator[YearUpdateDto].generate(YearUpdateDto, payload)
            year = Mapper[YearUpdateDto, Year].map(data, Year)
            response = await self.year_service.update(year)
            if not response.success:
                await self.year_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            year_mapped = Mapper[Year, YearResponseDto].map(
                response.data, YearResponseDto, True
            )
            await self.year_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=year_mapped,
            )
        except Exception as e:
            await self.year_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="YearController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request):
        try:
            await self.year_service.begin_transaction()
            year_id = request.path_params.get("year_id")
            if not year_id:
                await self.year_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Year ID is required",
                )
            year = Generator[Year].generate(Year, {"id": int(year_id)})
            response = await self.year_service.delete(year)
            if not response.success:
                await self.year_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.year_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Year deleted successfully",
            )
        except Exception as e:
            await self.year_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="YearController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
