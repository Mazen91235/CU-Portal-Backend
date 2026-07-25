from sqlalchemy import func
from core.iServices.iFacultyService import IFacultyService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.faculty import Faculty
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.facultyDtos import FacultySearchDto


class FacultyService(IFacultyService):
    def __init__(
        self,
        faculty_repository: IBaseRepository[Faculty],
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

    async def create(self, data: Faculty):
        try:
            if not data or not data.name or not data.name.strip():
                return BaseResponseDto(
                    success=False, code=400, message="Faculty name is required"
                )

            name = data.name.strip()
            existing_res = await self.faculty_repository.find_one(
                predicate=func.lower(Faculty.name) == name.lower()
            )
            if existing_res.success and existing_res.data:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Faculty already exists",
                )

            data.name = name
            create_res = await self.faculty_repository.create(data)
            if not create_res.success:
                return BaseResponseDto(
                    success=False,
                    code=create_res.code,
                    message=create_res.message,
                )

            return BaseResponseDto(success=True, code=201, data=create_res.data)
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

    async def update(self, data: Faculty):
        try:
            if not data or not data.name or not data.name.strip():
                return BaseResponseDto(
                    success=False, code=400, message="Faculty name is required"
                )

            name = data.name.strip()
            existing_res = await self.faculty_repository.find_one(
                predicate=func.lower(Faculty.name) == name.lower()
            )
            if (
                existing_res.success
                and existing_res.data
                and existing_res.data.id != data.id
            ):
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Faculty with this Name already exists",
                )

            target_res = await self.faculty_repository.find_one(
                predicate=(Faculty.id == data.id)
            )
            if not target_res.success or not target_res.data:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Faculty not found",
                )

            faculty = target_res.data
            faculty.name = name

            update_res = await self.faculty_repository.update(faculty, ["name"])
            if not update_res.success:
                return BaseResponseDto(
                    success=False,
                    code=update_res.code,
                    message=update_res.message,
                )

            return BaseResponseDto(success=True, code=200, data=update_res.data)
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

    async def delete(self, data: Faculty | None):
        try:
            if not data:
                return BaseResponseDto(
                    success=False, code=400, message="Faculty to delete is required"
                )

            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Faculty, ["users"]
            )
            result = await self.faculty_repository.find_one(
                predicate=(Faculty.id == data.id),
                includes=dynamic_includes,
            )
            if not result.success or not result.data:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Faculty not found",
                )

            faculty = result.data
            if faculty.users and len(faculty.users) > 0:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Faculty cannot be deleted because it has users associated with it",
                )

            delete_res = await self.faculty_repository.delete(faculty)
            if not delete_res.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_res.code,
                    message=delete_res.message,
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
