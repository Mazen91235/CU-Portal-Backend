from sqlalchemy import and_, func, between
from datetime import timedelta
from core.iServices.iWeekService import IWeekService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.week import Week
from core.dtos.baseDtos import BaseResponseDto


class WeekService(IWeekService):
    def __init__(
        self,
        week_repository: IBaseRepository[Week],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.week_repository = week_repository
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
                Week, data, [], is_and, starts_with, is_exact
            )
            if data and data.start_date_includes is not None:
                condition = between(
                    data.start_date_includes,
                    Week.start_date,
                    Week.start_date + timedelta(days=7),
                )
                predicate = (
                    and_(predicate, condition) if predicate is not None else condition
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Week, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Week", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Week", order_by, descending
            )
            result = await self.week_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
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
                Week, data, [], is_and, starts_with, is_exact
            )
            if data and data.start_date_includes is not None:
                condition = between(
                    data.start_date_includes,
                    Week.start_date,
                    Week.start_date + timedelta(days=7),
                )
                predicate = (
                    and_(predicate, condition) if predicate is not None else condition
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Week, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Week", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Week", order_by, descending
            )
            result = await self.week_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
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
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id,
                    department_id=data.department_id,
                    year_id=data.year_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Week",
                    level="error",
                    code=verify_restricted_access_response.code or 500,
                    message=f"Failed to verify restricted access for user: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=verify_restricted_access_response.code,
                    data=None,
                    message=verify_restricted_access_response.message,
                )
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
            existing_week = existing_week_response.data
            if existing_week:
                await self.logger.log(
                    action="Create",
                    entity="Week",
                    level="warning",
                    code=400,
                    message="Week already exists with the same details",
                    details={"week_number": data.week_number},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Week already exists with the same details",
                )
            nearest_distance = func.abs(
                func.extract("epoch", Week.start_date - data.start_date)
            )
            existing_week_withing_date_response = await self.week_repository.find_one(
                and_(
                    Week.faculty_id == data.faculty_id,
                    Week.department_id == data.department_id,
                    Week.year_id == data.year_id,
                ),
                order_by=[nearest_distance.asc()],
            )
            if not existing_week_withing_date_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_week_withing_date_response.code,
                    data=None,
                    message=existing_week_withing_date_response.message,
                )
            existing_week_within_date = existing_week_withing_date_response.data
            if (
                existing_week_within_date
                and abs(
                    (
                        (
                            existing_week_within_date.start_date - data.start_date
                        ).total_seconds()
                    )
                    / 86400
                )
                < 7
            ):
                await self.logger.log(
                    action="Create",
                    entity="Week",
                    level="warning",
                    code=400,
                    message="Another week already exists within 7 days of the provided start date",
                    details={
                        "existing_week_id": existing_week_within_date.id,
                        "existing_week_start_date": existing_week_within_date.start_date,
                        "new_week_start_date": data.start_date,
                    },
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Another week already exists within 7 days of the provided start date",
                )
            create_response = await self.week_repository.create(data)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            created_week = create_response.data
            if not created_week:
                await self.logger.log(
                    action="Create",
                    entity="Week",
                    level="error",
                    code=500,
                    message="Failed to create week",
                    details={"week_data": data},
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
                details={"week_id": created_week.id},
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
            target_week_response = await self.week_repository.find_one(
                Week.id == data.id
            )
            if not target_week_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_week_response.code,
                    data=None,
                    message=target_week_response.message,
                )
            target_week = target_week_response.data
            if not target_week:
                await self.logger.log(
                    action="Update",
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
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=target_week.faculty_id,
                    department_id=target_week.department_id,
                    year_id=target_week.year_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Week",
                    level="error",
                    code=verify_restricted_access_response.code or 500,
                    message=f"Failed to verify restricted access for user: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=verify_restricted_access_response.code,
                    data=None,
                    message=verify_restricted_access_response.message,
                )
            if (
                data.faculty_id != target_week.faculty_id
                or data.department_id != target_week.department_id
                or data.year_id != target_week.year_id
            ):
                await self.logger.log(
                    action="Update",
                    entity="Week",
                    level="error",
                    code=400,
                    message="Faculty, Department, and Year cannot be changed during update",
                    details={
                        "original_faculty_id": target_week.faculty_id,
                        "original_department_id": target_week.department_id,
                        "original_year_id": target_week.year_id,
                        "new_faculty_id": data.faculty_id,
                        "new_department_id": data.department_id,
                        "new_year_id": data.year_id,
                    },
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Faculty, Department, and Year cannot be changed during update",
                )
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
            existing_week = existing_week_response.data
            if existing_week and existing_week.id != data.id:
                await self.logger.log(
                    action="Update",
                    entity="Week",
                    level="warning",
                    code=400,
                    message="Another week already exists with the same details",
                    details={"week_number": data.week_number},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Another week already exists with the same details",
                )
            nearest_distance = func.abs(
                func.extract("epoch", Week.start_date - data.start_date)
            )
            existing_weeks_withing_date_response = await self.week_repository.find(
                and_(
                    Week.faculty_id == data.faculty_id,
                    Week.department_id == data.department_id,
                    Week.year_id == data.year_id,
                ),
                order_by=[nearest_distance.asc()],
                limit=2,
            )
            if not existing_weeks_withing_date_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_weeks_withing_date_response.code,
                    data=None,
                    message=existing_weeks_withing_date_response.message,
                )
            existing_weeks_within_date = existing_weeks_withing_date_response.data
            existing_week_within_date = None
            for week in existing_weeks_within_date or []:
                if week.id != data.id:
                    existing_week_within_date = week
                    break
            if (
                existing_week_within_date
                and abs(
                    (
                        (
                            existing_week_within_date.start_date - data.start_date
                        ).total_seconds()
                    )
                    / 86400
                )
                < 7
            ):
                await self.logger.log(
                    action="Update",
                    entity="Week",
                    level="warning",
                    code=400,
                    message="Another week already exists within 7 days of the provided start date",
                    details={
                        "existing_week_id": existing_week_within_date.id,
                        "existing_week_start_date": existing_week_within_date.start_date,
                        "new_week_start_date": data.start_date,
                    },
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Another week already exists within 7 days of the provided start date",
                )
            target_week.week_number = data.week_number
            target_week.start_date = data.start_date
            update_response = await self.week_repository.update(target_week)
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_week = update_response.data
            if not updated_week:
                await self.logger.log(
                    action="Update",
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
                action="Update",
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
                action="Update",
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
            target_week_response = await self.week_repository.find_one(
                Week.id == data.id, dynamic_includes
            )
            if not target_week_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_week_response.code,
                    data=None,
                    message=target_week_response.message,
                )
            target_week = target_week_response.data
            if not target_week:
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
            if target_week.materials and len(target_week.materials) > 0:
                await self.logger.log(
                    action="Delete",
                    entity="Week",
                    level="warning",
                    code=400,
                    message="Cannot delete week with associated materials",
                    details={
                        "week_id": data.id,
                        "material_count": len(target_week.materials),
                    },
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Cannot delete week with associated materials",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=target_week.faculty_id,
                    department_id=target_week.department_id,
                    year_id=target_week.year_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Week",
                    level="error",
                    code=verify_restricted_access_response.code or 500,
                    message=f"Failed to verify restricted access for user: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="WeekService",
                )
                return BaseResponseDto(
                    success=False,
                    code=verify_restricted_access_response.code,
                    data=None,
                    message=verify_restricted_access_response.message,
                )
            delete_response = await self.week_repository.delete(target_week)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
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
