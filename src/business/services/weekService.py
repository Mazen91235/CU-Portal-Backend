from typing import cast
from sqlalchemy import and_

from core.iServices.iWeekService import IWeekService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.week import Week
from core.entities.faculty import Faculty
from core.entities.department import Department
from core.entities.year import Year
from core.dtos.baseDtos import BaseResponseDto


class WeekService(IWeekService):
    def __init__(
        self,
        week_repository: IBaseRepository[Week],
        faculty_repository: IBaseRepository[Faculty],
        department_repository: IBaseRepository[Department],
        year_repository: IBaseRepository[Year],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.week_repository = week_repository
        self.faculty_repository = faculty_repository
        self.department_repository = department_repository
        self.year_repository = year_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.week_repository.begin_transaction()

    async def commit_transaction(self):
        await self.week_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.week_repository.rollback_transaction()

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
                Week, data, ["week_number"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Week, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Week", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Week", order_by
            )
            result = await self.week_repository.find_one(
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
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while finding week",
                details={"error": repr(ex)},
                source="WeekService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding week",
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
                Week, data, ["week_number"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Week, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Week", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Week", order_by
            )
            result = await self.week_repository.find(
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
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while finding weeks",
                details={"error": repr(ex)},
                source="WeekService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding weeks",
            )

    async def create(self, data):
        try:
            # Verify Faculty exists
            faculty_response = await self.faculty_repository.find_one(
                Faculty.id == data.faculty_id
            )
            if not faculty_response.success or not faculty_response.data:
                await self.logger.log(
                    action="Create",
                    entity="Week",
                    level="warning",
                    code=404,
                    message=f"Faculty with ID {data.faculty_id} not found",
                    details={"faculty_id": data.faculty_id},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Faculty with ID {data.faculty_id} not found",
                )

            # Verify Department exists
            dept_response = await self.department_repository.find_one(
                Department.id == data.department_id
            )
            if not dept_response.success or not dept_response.data:
                await self.logger.log(
                    action="Create",
                    entity="Week",
                    level="warning",
                    code=404,
                    message=f"Department with ID {data.department_id} not found",
                    details={"department_id": data.department_id},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Department with ID {data.department_id} not found",
                )

            # Verify Year exists
            year_response = await self.year_repository.find_one(
                Year.id == data.year_id
            )
            if not year_response.success or not year_response.data:
                await self.logger.log(
                    action="Create",
                    entity="Week",
                    level="warning",
                    code=404,
                    message=f"Year with ID {data.year_id} not found",
                    details={"year_id": data.year_id},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Year with ID {data.year_id} not found",
                )

            # Check if Week already exists with same (faculty_id, department_id, year_id, week_number)
            existing_week_response = await self.week_repository.find_one(
                and_(
                    Week.faculty_id == data.faculty_id,
                    Week.department_id == data.department_id,
                    Week.year_id == data.year_id,
                    Week.week_number == data.week_number,
                )
            )
            if not existing_week_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_week_response.code,
                    data=None,
                    message=existing_week_response.message,
                )
            if existing_week_response.data:
                await self.logger.log(
                    action="Create",
                    entity="Week",
                    level="warning",
                    code=400,
                    message="Week number already exists for this faculty, department, and year",
                    details={
                        "faculty_id": data.faculty_id,
                        "department_id": data.department_id,
                        "year_id": data.year_id,
                        "week_number": data.week_number,
                    },
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Week number already exists for this faculty, department, and year",
                )

            result = await self.week_repository.create(data)
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            created_week = result.data
            if not created_week:
                await self.logger.log(
                    action="Create",
                    entity="Week",
                    level="error",
                    code=500,
                    message="Failed to create week",
                    details={"week_number": data.week_number},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to create week",
                )
            await self.logger.log(
                action="Create",
                entity="Week",
                level="info",
                code=201,
                message="Week created successfully",
                details={"week_id": created_week.id, "week_number": data.week_number},
                source="WeekService",
            )
            return BaseResponseDto(success=True, code=201, data=created_week)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while creating week",
                details={"error": repr(ex)},
                source="WeekService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating week",
            )

    async def update(self, data):
        try:
            week_response = await self.week_repository.find_one(Week.id == data.id)
            if not week_response.success:
                return BaseResponseDto(
                    success=False,
                    code=week_response.code,
                    data=None,
                    message=week_response.message,
                )
            week = week_response.data
            if not week:
                await self.logger.log(
                    action="Edit",
                    entity="Week",
                    level="warning",
                    code=404,
                    message="Week not found for update",
                    details={"week_id": data.id},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Week not found",
                )

            faculty_id = data.faculty_id if data.faculty_id is not None else week.faculty_id
            department_id = (
                data.department_id if data.department_id is not None else week.department_id
            )
            year_id = data.year_id if data.year_id is not None else week.year_id
            week_number = (
                data.week_number if data.week_number is not None else week.week_number
            )

            # Check Faculty existence if changed
            if data.faculty_id is not None and data.faculty_id != week.faculty_id:
                fac_res = await self.faculty_repository.find_one(Faculty.id == data.faculty_id)
                if not fac_res.success or not fac_res.data:
                    return BaseResponseDto(
                        success=False, code=404, message=f"Faculty with ID {data.faculty_id} not found"
                    )

            # Check Department existence if changed
            if data.department_id is not None and data.department_id != week.department_id:
                dept_res = await self.department_repository.find_one(
                    Department.id == data.department_id
                )
                if not dept_res.success or not dept_res.data:
                    return BaseResponseDto(
                        success=False, code=404, message=f"Department with ID {data.department_id} not found"
                    )

            # Check Year existence if changed
            if data.year_id is not None and data.year_id != week.year_id:
                year_res = await self.year_repository.find_one(Year.id == data.year_id)
                if not year_res.success or not year_res.data:
                    return BaseResponseDto(
                        success=False, code=404, message=f"Year with ID {data.year_id} not found"
                    )

            # Check duplicate
            existing_response = await self.week_repository.find_one(
                and_(
                    Week.faculty_id == faculty_id,
                    Week.department_id == department_id,
                    Week.year_id == year_id,
                    Week.week_number == week_number,
                )
            )
            if not existing_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_response.code,
                    data=None,
                    message=existing_response.message,
                )
            existing_week = existing_response.data
            if existing_week and existing_week.id != data.id:
                await self.logger.log(
                    action="Edit",
                    entity="Week",
                    level="warning",
                    code=400,
                    message="Another week with the same details already exists",
                    details={"week_id": data.id, "week_number": week_number},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Another week with the same details already exists",
                )

            fields_to_update = []
            if data.week_number is not None:
                week.week_number = data.week_number
                fields_to_update.append("week_number")
            if data.start_date is not None:
                week.start_date = data.start_date
                fields_to_update.append("start_date")
            if data.end_date is not None:
                week.end_date = data.end_date
                fields_to_update.append("end_date")
            if data.faculty_id is not None:
                week.faculty_id = data.faculty_id
                fields_to_update.append("faculty_id")
            if data.department_id is not None:
                week.department_id = data.department_id
                fields_to_update.append("department_id")
            if data.year_id is not None:
                week.year_id = data.year_id
                fields_to_update.append("year_id")

            if not fields_to_update:
                return BaseResponseDto(success=True, code=200, data=week)

            result = await self.week_repository.update(week, fields_to_update)
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )

            updated_week = result.data
            if not updated_week:
                await self.logger.log(
                    action="Edit",
                    entity="Week",
                    level="error",
                    code=500,
                    message="Failed to update week",
                    details={"week_id": data.id},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to update week",
                )

            await self.logger.log(
                action="Edit",
                entity="Week",
                level="info",
                code=200,
                message="Week updated successfully",
                details={"week_id": data.id},
                source="WeekService",
            )
            return BaseResponseDto(success=True, code=200, data=updated_week)
        except Exception as ex:
            await self.logger.log(
                action="Edit",
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while updating week",
                details={"error": repr(ex)},
                source="WeekService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating week",
            )

    async def delete(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Week, ["materials"]
            )
            week_response = await self.week_repository.find_one(
                Week.id == data.id, dynamic_includes
            )
            if not week_response.success:
                return BaseResponseDto(
                    success=False,
                    code=week_response.code,
                    data=None,
                    message=week_response.message,
                )

            week = week_response.data
            if not week:
                await self.logger.log(
                    action="Delete",
                    entity="Week",
                    level="warning",
                    code=404,
                    message="Week not found for deletion",
                    details={"week_id": data.id},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Week not found",
                )

            result = await self.week_repository.delete(week)
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            await self.logger.log(
                action="Delete",
                entity="Week",
                level="info",
                code=200,
                message="Week deleted successfully",
                details={"week_id": data.id},
                source="WeekService",
            )
            return BaseResponseDto(success=True, code=200, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Week",
                level="error",
                code=500,
                message="An error occurred while deleting week",
                details={"error": repr(ex)},
                source="WeekService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting week",
            )
