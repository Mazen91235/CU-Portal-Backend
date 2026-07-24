from typing import cast

from core.iServices.iYearService import IYearService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.year import Year
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.yearDtos import YearSearchDto


class YearService(IYearService):
    def __init__(
        self,
        year_repository: IBaseRepository[Year],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.year_repository = year_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.year_repository.begin_transaction()

    async def commit_transaction(self):
        await self.year_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.year_repository.rollback_transaction()

    # CRUD Functions
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
                Year, data, None, is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Year, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Year", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Year", order_by
            )
            result = await self.year_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            return BaseResponseDto(success=True, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while finding academic year",
                details={"error": str(ex)},
                source="YearService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding academic year",
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
                Year, data, None, is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Year, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Year", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Year", order_by
            )
            result = await self.year_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
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
            return BaseResponseDto(success=True, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while finding academic years",
                details={"error": str(ex)},
                source="YearService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding academic years",
            )

    async def create(self, data: Year):
        try:
            existing_response = await self.year_repository.find_one(Year.year == data.year)
            if existing_response.success and existing_response.data:
                await self.logger.log(
                    action="Add",
                    entity="Year",
                    level="warning",
                    code=400,
                    message="Year already exists",
                    details={"year": data.year},
                    source="YearService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Year already exists",
                )

            result = await self.year_repository.create(data)
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            await self.logger.log(
                action="Add",
                entity="Year",
                level="info",
                code=201,
                message="Year created successfully",
                details={"year": data.year},
                source="YearService",
            )
            return BaseResponseDto(success=True, code=201, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="Add",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while creating academic year",
                details={"error": str(ex)},
                source="YearService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating academic year",
            )

    async def update(self, data: Year):
        try:
            year_response = await self.year_repository.find_one(Year.id == data.id)
            if not year_response.success or not year_response.data:
                await self.logger.log(
                    action="Edit",
                    entity="Year",
                    level="warning",
                    code=404,
                    message="Year not found for update",
                    details={"year_id": data.id},
                    source="YearService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Year not found",
                )

            existing_response = await self.year_repository.find_one(Year.year == data.year)
            if existing_response.success and existing_response.data:
                existing_year = existing_response.data
                if existing_year.id != data.id:
                    await self.logger.log(
                        action="Edit",
                        entity="Year",
                        level="warning",
                        code=400,
                        message="Year already exists for update",
                        details={"year": data.year},
                        source="YearService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Year already exists",
                    )

            year_obj = year_response.data
            year_obj.year = data.year

            result = await self.year_repository.update(year_obj)
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            await self.logger.log(
                action="Edit",
                entity="Year",
                level="info",
                code=200,
                message="Year updated successfully",
                details={"year_id": data.id, "year": data.year},
                source="YearService",
            )
            return BaseResponseDto(success=True, code=200, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="Edit",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while updating academic year",
                details={"error": str(ex)},
                source="YearService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating academic year",
            )

    async def delete(self, data: Year | None):
        try:
            if not data or not data.id:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Year not found",
                )

            dynamic_includes = self.helper_service.generate_dynamic_includes(Year, ["users"])
            year_response = await self.year_repository.find_one(Year.id == data.id, dynamic_includes)
            if not year_response.success or not year_response.data:
                await self.logger.log(
                    action="Delete",
                    entity="Year",
                    level="warning",
                    code=404,
                    message="Year not found for deletion",
                    details={"year_id": data.id},
                    source="YearService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Year not found",
                )

            year = year_response.data
            if year.users and len(year.users) > 0:
                await self.logger.log(
                    action="Delete",
                    entity="Year",
                    level="warning",
                    code=400,
                    message="Year cannot be deleted because it has users associated with it",
                    details={"year_id": data.id, "users_count": len(year.users)},
                    source="YearService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Year cannot be deleted because it has users associated with it",
                )

            result = await self.year_repository.delete(year)
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            await self.logger.log(
                action="Delete",
                entity="Year",
                level="info",
                code=200,
                message="Year deleted successfully",
                details={"year_id": data.id},
                source="YearService",
            )
            return BaseResponseDto(success=True, code=200, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Year",
                level="error",
                code=500,
                message="An error occurred while deleting academic year",
                details={"error": str(ex)},
                source="YearService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting academic year",
            )
