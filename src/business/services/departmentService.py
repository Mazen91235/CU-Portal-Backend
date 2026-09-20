from typing import cast
from sqlalchemy import func, and_, or_

from core.iServices.iDepartmentService import IDepartmentService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.department import Department
from core.entities.faculty import Faculty
from core.dtos.baseDtos import BaseResponseDto


class DepartmentService(IDepartmentService):
    def __init__(
        self,
        department_repository: IBaseRepository[Department],
        faculty_repository: IBaseRepository[Faculty],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.department_repository = department_repository
        self.faculty_repository = faculty_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.department_repository.begin_transaction()

    async def commit_transaction(self):
        await self.department_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.department_repository.rollback_transaction()

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
                Department, data, ["name", "code"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Department, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Department", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Department", order_by, descending
            )
            result = await self.department_repository.find_one(
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
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while finding department",
                details={"error": repr(ex)},
                source="DepartmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding department",
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
                Department, data, ["name", "code"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Department, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Department", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Department", order_by, descending
            )
            result = await self.department_repository.find(
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
            return BaseResponseDto(success=True, data=result.data, next_page=result.next_page)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while finding departments",
                details={"error": repr(ex)},
                source="DepartmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding departments",
            )

    async def create(self, data):
        try:
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Department",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user on faculty {data.faculty_id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to create department for this faculty.",
                )
            faculty_response = await self.faculty_repository.find_one(
                Faculty.id == data.faculty_id
            )
            if not faculty_response.success:
                return BaseResponseDto(
                    success=False,
                    code=faculty_response.code,
                    message=faculty_response.message,
                )

            faculty = faculty_response.data
            if not faculty:
                await self.logger.log(
                    action="Create",
                    entity="Department",
                    level="warning",
                    code=404,
                    message="Faculty not found for department creation",
                    details={},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Faculty not found",
                )

            existing_department_response = None

            if data.study_type != Department.StudyType.BOTH:
                existing_department_response = (
                    await self.department_repository.find_one(
                        and_(
                            (Department.faculty_id == data.faculty_id),
                            (
                                func.lower(Department.study_type)
                                == data.study_type.lower()
                            ),
                            or_(
                                (func.lower(Department.name) == data.name.lower()),
                                (func.lower(Department.code) == data.code.lower()),
                            ),
                        )
                    )
                )
            else:
                existing_department_response = (
                    await self.department_repository.find_one(
                        and_(
                            (Department.faculty_id == data.faculty_id),
                            or_(
                                (func.lower(Department.name) == data.name.lower()),
                                (func.lower(Department.code) == data.code.lower()),
                            ),
                        )
                    )
                )

            if not existing_department_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_department_response.code,
                    data=None,
                    message=existing_department_response.message,
                )

            existing_department = existing_department_response.data
            if existing_department:
                await self.logger.log(
                    action="Create",
                    entity="Department",
                    level="warning",
                    code=400,
                    message="Department with this Name or Code already exists for this Faculty.",
                    details={},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Department with this Name or Code already exists for this Faculty",
                )

            if data.study_type != Department.StudyType.BOTH:
                create_department_response = await self.department_repository.create(
                    data
                )
                if not create_department_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=create_department_response.code,
                        data=None,
                        message=create_department_response.message,
                    )
                created_department = create_department_response.data
                if not created_department:
                    await self.logger.log(
                        action="Create",
                        entity="Department",
                        level="error",
                        code=500,
                        message="Failed to create department.",
                        details={},
                        source="DepartmentService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        message="Failed to create department",
                    )
            else:
                data.study_type = Department.StudyType.MAINSTREAM
                create_mainstream_response = await self.department_repository.create(
                    data
                )
                if not create_mainstream_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=create_mainstream_response.code,
                        data=None,
                        message=create_mainstream_response.message,
                    )
                created_mainstream_department = create_mainstream_response.data
                if not created_mainstream_department:
                    await self.logger.log(
                        action="Create",
                        entity="Department",
                        level="error",
                        code=500,
                        message="Failed to create mainstream department.",
                        details={},
                        source="DepartmentService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        message="Failed to create mainstream department",
                    )
                data.study_type = Department.StudyType.CREDIT
                create_credit_response = await self.department_repository.create(data)
                if not create_credit_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=create_credit_response.code,
                        data=None,
                        message=create_credit_response.message,
                    )
                created_credit_department = create_credit_response.data
                if not created_credit_department:
                    await self.logger.log(
                        action="Create",
                        entity="Department",
                        level="error",
                        code=500,
                        message="Failed to create credit department.",
                        details={},
                        source="DepartmentService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        message="Failed to create credit department",
                    )
                created_department = created_mainstream_department

            await self.logger.log(
                action="Create",
                entity="Department",
                level="info",
                code=201,
                message="Department Created Successfully.",
                details={},
                source="DepartmentService",
            )
            return BaseResponseDto(success=True, code=201, data=created_department)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while creating department",
                details={"error": repr(ex)},
                source="DepartmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating department",
            )

    async def update(self, data):
        try:
            department_response = await self.department_repository.find_one(
                Department.id == data.id
            )
            if not department_response.success:
                return BaseResponseDto(
                    success=False,
                    code=department_response.code,
                    data=None,
                    message=department_response.message,
                )
            department = department_response.data
            if not department:
                await self.logger.log(
                    action="Update",
                    entity="Department",
                    level="warning",
                    code=404,
                    message="Department not found for update.",
                    details={"department_id": data.id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Department not found for update",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Department",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user on faculty {data.faculty_id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to update department for this faculty.",
                )
            faculty_response = await self.faculty_repository.find_one(
                Faculty.id == data.faculty_id
            )
            if not faculty_response.success:
                return BaseResponseDto(
                    success=False,
                    code=faculty_response.code,
                    data=None,
                    message=faculty_response.message,
                )
            faculty = faculty_response.data
            if not faculty:
                await self.logger.log(
                    action="Update",
                    entity="Department",
                    level="warning",
                    code=404,
                    message="Faculty not found for department update",
                    details={},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Faculty not found",
                )
            existing_department_response = None
            if data.study_type != Department.StudyType.BOTH:
                existing_department_response = (
                    await self.department_repository.find_one(
                        and_(
                            (Department.faculty_id == data.faculty_id),
                            (
                                func.lower(Department.study_type)
                                == data.study_type.lower()
                            ),
                            or_(
                                (func.lower(Department.name) == data.name.lower()),
                                (func.lower(Department.code) == data.code.lower()),
                            ),
                        )
                    )
                )
            else:
                existing_department_response = (
                    await self.department_repository.find_one(
                        and_(
                            (Department.faculty_id == data.faculty_id),
                            or_(
                                (func.lower(Department.name) == data.name.lower()),
                                (func.lower(Department.code) == data.code.lower()),
                            ),
                        )
                    )
                )
            if not existing_department_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_department_response.code,
                    data=None,
                    message=existing_department_response.message,
                )
            existing_department = existing_department_response.data
            if existing_department and existing_department.id != data.id:
                await self.logger.log(
                    action="Update",
                    entity="Department",
                    level="warning",
                    code=400,
                    message="Another department with this Name or Code already exists for this Faculty.",
                    details={},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Another department with this Name or Code already exists for this Faculty",
                )
            department.name = data.name
            department.code = data.code
            department.faculty_id = data.faculty_id
            department.study_type = data.study_type
            update_response = await self.department_repository.update(
                department, ["name", "code", "faculty_id", "study_type"]
            )
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_department = update_response.data
            if not updated_department:
                await self.logger.log(
                    action="Update",
                    entity="Department",
                    level="error",
                    code=500,
                    message="Failed to update department.",
                    details={},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    message="Failed to update department",
                )
            await self.logger.log(
                action="Update",
                entity="Department",
                level="info",
                code=200,
                message="Department updated successfully.",
                details={},
                source="DepartmentService",
            )
            return BaseResponseDto(success=True, code=200, data=updated_department)
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while updating department",
                details={"error": repr(ex)},
                source="DepartmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating department",
            )

    async def delete(self, data):
        try:
            if not data:
                await self.logger.log(
                    action="Delete",
                    entity="Department",
                    level="warning",
                    code=400,
                    message="No data provided for department deletion.",
                    details={},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="No data provided for deletion",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Department, ["users"]
            )
            department_response = await self.department_repository.find_one(
                Department.id == data.id, dynamic_includes
            )
            if not department_response.success:
                return BaseResponseDto(
                    success=False,
                    code=department_response.code,
                    data=None,
                    message=department_response.message,
                )

            department = department_response.data
            if not department:
                await self.logger.log(
                    action="Delete",
                    entity="Department",
                    level="warning",
                    code=404,
                    message="Department not found for deletion.",
                    details={"department_id": data.id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Department not found for deletion",
                )

            if department.users and len(department.users) > 0:
                await self.logger.log(
                    action="Delete",
                    entity="Department",
                    level="warning",
                    code=400,
                    message="Department Cannot Be Deleted Because It Has Users Associated with It.",
                    details={
                        "department_id": data.id,
                        "users_count": len(department.users),
                    },
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Department cannot be deleted because it has users associated with it",
                )

            result = await self.department_repository.delete(department)
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            await self.logger.log(
                action="Delete",
                entity="Department",
                level="info",
                code=200,
                message="Department Deleted Successfully.",
                details={"department_id": data.id},
                source="DepartmentService",
            )
            return BaseResponseDto(success=True, code=200, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while deleting department",
                details={"error": repr(ex)},
                source="DepartmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting department",
            )
