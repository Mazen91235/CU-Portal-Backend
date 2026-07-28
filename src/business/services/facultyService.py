from sqlalchemy import func
from core.iServices.iFacultyService import IFacultyService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.faculty import Faculty
from core.dtos.baseDtos import BaseResponseDto


class FacultyService(IFacultyService):
    def __init__(
        self,
        faculty_repository: IBaseRepository,
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.faculty_repository = faculty_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.faculty_repository.begin_transaction()

    async def commit_transaction(self):
        await self.faculty_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.faculty_repository.rollback_transaction()

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
                Faculty, data, ["name"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Faculty, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Faculty", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Faculty", order_by
            )
            result = await self.faculty_repository.find_one(
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
            faculty = result.data
            return BaseResponseDto(success=True, data=faculty)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while finding faculty",
                details={"error": str(ex)},
                source="FacultyService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding faculty",
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
                Faculty, data, ["name"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Faculty, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Faculty", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Faculty", order_by
            )
            result = await self.faculty_repository.find(
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
            faculties = result.data
            return BaseResponseDto(success=True, data=faculties)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while finding faculties",
                details={"error": str(ex)},
                source="FacultyService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding faculties",
            )

    async def create(self, data):
        try:
            name = data.name.strip()
            data.name = name

            existing_res = await self.faculty_repository.find_one(
                func.lower(Faculty.name) == name.lower()
            )
            if not existing_res.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_res.code,
                    data=None,
                    message=existing_res.message,
                )
            existing_faculty = existing_res.data
            if existing_faculty:
                await self.logger.log(
                    action="Create",
                    entity="Faculty",
                    level="warning",
                    code=400,
                    message="Faculty already exists",
                    source="FacultyService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Faculty already exists",
                )

            create_res = await self.faculty_repository.create(data)
            if not create_res.success:
                return BaseResponseDto(
                    success=False,
                    code=create_res.code,
                    data=None,
                    message=create_res.message,
                )
            created_faculty = create_res.data
            if not created_faculty:
                await self.logger.log(
                    action="Create",
                    entity="Faculty",
                    level="error",
                    code=500,
                    message="Failed to create faculty without a specific error",
                    source="FacultyService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating faculty",
                )

            await self.logger.log(
                action="Create",
                entity="Faculty",
                level="info",
                code=201,
                message="Faculty created successfully",
                source="FacultyService",
            )
            return BaseResponseDto(success=True, code=201, data=created_faculty)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while creating faculty",
                details={"error": str(ex)},
                source="FacultyService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating faculty",
            )

    async def update(self, data):
        try:
            name = data.name.strip()

            target_res = await self.faculty_repository.find_one(
                Faculty.id == data.id
            )
            if not target_res.success:
                return BaseResponseDto(
                    success=False,
                    code=target_res.code,
                    data=None,
                    message=target_res.message,
                )
            target_faculty = target_res.data
            if not target_faculty:
                await self.logger.log(
                    action="Update",
                    entity="Faculty",
                    level="info",
                    code=404,
                    message="Faculty not found",
                    source="FacultyService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Faculty not found",
                )

            existing_res = await self.faculty_repository.find_one(
                func.lower(Faculty.name) == name.lower()
            )
            if not existing_res.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_res.code,
                    data=None,
                    message=existing_res.message,
                )
            existing_faculty = existing_res.data
            if existing_faculty and existing_faculty.id != data.id:
                await self.logger.log(
                    action="Update",
                    entity="Faculty",
                    level="warning",
                    code=400,
                    message="Faculty with this name already exists",
                    source="FacultyService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Faculty with this name already exists",
                )

            target_faculty.name = name

            update_res = await self.faculty_repository.update(target_faculty, ["name"])
            if not update_res.success:
                return BaseResponseDto(
                    success=False,
                    code=update_res.code,
                    message=update_res.message,
                )
            updated_faculty = update_res.data
            if not updated_faculty:
                await self.logger.log(
                    action="Update",
                    entity="Faculty",
                    level="error",
                    code=500,
                    message="Failed to update faculty without a specific error",
                    source="FacultyService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating faculty",
                )

            await self.logger.log(
                action="Update",
                entity="Faculty",
                level="info",
                code=200,
                message="Faculty updated successfully",
                source="FacultyService",
            )
            return BaseResponseDto(success=True, code=200, data=updated_faculty)
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while updating faculty",
                details={"error": str(ex)},
                source="FacultyService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating faculty",
            )

    async def delete(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Faculty, ["users"]
            )
            result = await self.faculty_repository.find_one(
                predicate=(Faculty.id == data.id),
                includes=dynamic_includes,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            faculty = result.data
            if not faculty:
                await self.logger.log(
                    action="Delete",
                    entity="Faculty",
                    level="info",
                    code=404,
                    message="Faculty not found",
                    source="FacultyService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Faculty not found",
                )

            if faculty.users and len(faculty.users) > 0:
                await self.logger.log(
                    action="Delete",
                    entity="Faculty",
                    level="warning",
                    code=400,
                    message="Faculty cannot be deleted because it has users associated with it",
                    source="FacultyService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Faculty cannot be deleted because it has users associated with it",
                )

            delete_res = await self.faculty_repository.delete(faculty)
            if not delete_res.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_res.code,
                    data=None,
                    message=delete_res.message,
                )

            await self.logger.log(
                action="Delete",
                entity="Faculty",
                level="info",
                code=200,
                message="Faculty deleted successfully",
                source="FacultyService",
            )
            return BaseResponseDto(success=True, code=200, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while deleting faculty",
                details={"error": str(ex)},
                source="FacultyService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting faculty",
            )
