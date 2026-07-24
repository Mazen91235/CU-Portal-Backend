from typing import cast
from sqlalchemy import func

from core.iServices.iDepartmentService import IDepartmentService
from core.iServices.iUserService import IUserService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.department import Department
from core.entities.faculty import Faculty
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.departmentDtos import DepartmentSearchDto


class DepartmentService(IDepartmentService):
    def __init__(
        self,
        department_repository: IBaseRepository[Department],
        faculty_repository: IBaseRepository[Faculty],
        user_service: IUserService,
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.department_repository = department_repository
        self.faculty_repository = faculty_repository
        self.user_service = user_service
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
                "Department", order_by
            )
            result = await self.department_repository.find_one(
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
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while finding department",
                details={"error": str(ex)},
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
                "Department", order_by
            )
            result = await self.department_repository.find(
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
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while finding departments",
                details={"error": str(ex)},
                source="DepartmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding departments",
            )

    async def create(self, data: Department):
        try:
            # 1. Permission checks
            permissions_response = await self.user_service.get_user_permissions()
            if not permissions_response.success:
                return BaseResponseDto(
                    success=False,
                    code=permissions_response.code or 403,
                    message=permissions_response.message or "Unauthorized to create department",
                )
            permissions = permissions_response.data or []
            can_access_all_faculties = "Access All Faculties" in permissions

            # 2. Check current user and constraints
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success or not logged_in_user_response.data:
                return BaseResponseDto(
                    success=False,
                    code=401,
                    message="User not logged in",
                )
            current_user = logged_in_user_response.data

            if data.faculty_id != current_user.faculty_id and not can_access_all_faculties:
                await self.logger.log(
                    action="Add",
                    entity="Department",
                    level="warning",
                    code=403,
                    message="User does not have access to change the faculty for department creation.",
                    details={"faculty_id": data.faculty_id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="You do not have access to select faculty rather than your own",
                )

            # 3. Check faculty existence
            faculty_response = await self.faculty_repository.find_one(Faculty.id == data.faculty_id)
            if not faculty_response.success or not faculty_response.data:
                await self.logger.log(
                    action="Add",
                    entity="Department",
                    level="warning",
                    code=404,
                    message="Faculty not found for department creation",
                    details={"faculty_id": data.faculty_id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Faculty not found",
                )

            # 4. Check duplicates
            if data.study_type != "Both":
                existing_name_res = await self.department_repository.find_one(
                    (Department.faculty_id == data.faculty_id)
                    & (func.lower(Department.study_type) == data.study_type.lower())
                    & (func.lower(Department.name) == data.name.lower())
                )
                existing_code_res = await self.department_repository.find_one(
                    (Department.faculty_id == data.faculty_id)
                    & (func.lower(Department.study_type) == data.study_type.lower())
                    & (func.lower(Department.code) == data.code.lower())
                )
            else:
                existing_name_res = await self.department_repository.find_one(
                    (Department.faculty_id == data.faculty_id)
                    & (func.lower(Department.name) == data.name.lower())
                )
                existing_code_res = await self.department_repository.find_one(
                    (Department.faculty_id == data.faculty_id)
                    & (func.lower(Department.code) == data.code.lower())
                )

            if existing_name_res.success and existing_name_res.data:
                await self.logger.log(
                    action="Add",
                    entity="Department",
                    level="warning",
                    code=400,
                    message="Department Name Already Exists with this Type for this Faculty.",
                    details={"name": data.name, "faculty_id": data.faculty_id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Department with this Name already exists with this type for this faculty",
                )

            if existing_code_res.success and existing_code_res.data:
                await self.logger.log(
                    action="Add",
                    entity="Department",
                    level="warning",
                    code=400,
                    message="Department Code Already Exists with this Type for this Faculty.",
                    details={"code": data.code, "faculty_id": data.faculty_id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Department with this Code already exists with this type for this faculty",
                )

            # 5. Save department record(s)
            created_dept = None
            if data.study_type != "Both":
                dept = Department(
                    name=data.name,
                    faculty_id=data.faculty_id,
                    study_type=data.study_type,
                    code=data.code.upper(),
                )
                result = await self.department_repository.create(dept)
                if not result.success:
                    return BaseResponseDto(
                        success=False,
                        code=result.code,
                        data=None,
                        message=result.message,
                    )
                created_dept = result.data
            else:
                dept_mainstream = Department(
                    name=data.name,
                    faculty_id=data.faculty_id,
                    study_type="Mainstream",
                    code=data.code.upper(),
                )
                result_mainstream = await self.department_repository.create(dept_mainstream)
                if not result_mainstream.success:
                    return BaseResponseDto(
                        success=False,
                        code=result_mainstream.code,
                        data=None,
                        message=result_mainstream.message,
                    )
                dept_credit = Department(
                    name=data.name,
                    faculty_id=data.faculty_id,
                    study_type="Credit",
                    code=data.code.upper(),
                )
                result_credit = await self.department_repository.create(dept_credit)
                if not result_credit.success:
                    return BaseResponseDto(
                        success=False,
                        code=result_credit.code,
                        data=None,
                        message=result_credit.message,
                    )
                created_dept = result_mainstream.data

            await self.logger.log(
                action="Add",
                entity="Department",
                level="info",
                code=201,
                message="Department Created Successfully.",
                details={"name": data.name, "faculty_id": data.faculty_id},
                source="DepartmentService",
            )
            return BaseResponseDto(success=True, code=201, data=created_dept)
        except Exception as ex:
            await self.logger.log(
                action="Add",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while creating department",
                details={"error": str(ex)},
                source="DepartmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating department",
            )

    async def update(self, data: Department):
        try:
            # 1. Check if exists
            dept_res = await self.department_repository.find_one(Department.id == data.id)
            if not dept_res.success or not dept_res.data:
                await self.logger.log(
                    action="Edit",
                    entity="Department",
                    level="warning",
                    code=404,
                    message="Department Not Found for Update.",
                    details={"department_id": data.id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Department not found",
                )
            department = dept_res.data

            # 2. Permissions check
            permissions_response = await self.user_service.get_user_permissions()
            if not permissions_response.success:
                return BaseResponseDto(
                    success=False,
                    code=permissions_response.code or 403,
                    message=permissions_response.message or "Unauthorized to update department",
                )
            permissions = permissions_response.data or []
            can_access_all_faculties = "Access All Faculties" in permissions

            # 3. Faculty constraints
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success or not logged_in_user_response.data:
                return BaseResponseDto(
                    success=False,
                    code=401,
                    message="User not logged in",
                )
            current_user = logged_in_user_response.data

            if data.faculty_id != current_user.faculty_id and not can_access_all_faculties:
                await self.logger.log(
                    action="Edit",
                    entity="Department",
                    level="warning",
                    code=403,
                    message="User does not have access to change the faculty for department update.",
                    details={"faculty_id": data.faculty_id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="You do not have access to select faculty rather than your own",
                )

            # 4. Check faculty existence
            faculty_response = await self.faculty_repository.find_one(Faculty.id == data.faculty_id)
            if not faculty_response.success or not faculty_response.data:
                await self.logger.log(
                    action="Edit",
                    entity="Department",
                    level="warning",
                    code=404,
                    message="Faculty not found for department update",
                    details={"faculty_id": data.faculty_id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Faculty not found",
                )

            # 5. Check duplicate name / code
            existing_name_res = await self.department_repository.find_one(
                (Department.faculty_id == department.faculty_id)
                & (func.lower(Department.study_type) == data.study_type.lower())
                & (func.lower(Department.name) == data.name.lower())
            )
            if existing_name_res.success and existing_name_res.data:
                existing_dept = existing_name_res.data
                if existing_dept.id != data.id:
                    await self.logger.log(
                        action="Edit",
                        entity="Department",
                        level="warning",
                        code=400,
                        message="Department Name Already Exists with this Type for this Faculty.",
                        details={"name": data.name, "faculty_id": data.faculty_id},
                        source="DepartmentService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        message="Department with this Name already exists with this type for this faculty",
                    )

            existing_code_res = await self.department_repository.find_one(
                (Department.faculty_id == department.faculty_id)
                & (func.lower(Department.study_type) == data.study_type.lower())
                & (func.lower(Department.code) == data.code.lower())
            )
            if existing_code_res.success and existing_code_res.data:
                existing_dept = existing_code_res.data
                if existing_dept.id != data.id:
                    await self.logger.log(
                        action="Edit",
                        entity="Department",
                        level="warning",
                        code=400,
                        message="Department Code Already Exists with this Type for this Faculty.",
                        details={"code": data.code, "faculty_id": data.faculty_id},
                        source="DepartmentService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        message="Department with this Code already exists with this type for this faculty",
                    )

            # 6. Apply updates
            department.name = data.name
            department.faculty_id = data.faculty_id
            department.study_type = data.study_type
            department.code = data.code.upper()

            result = await self.department_repository.update(department)
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            await self.logger.log(
                action="Edit",
                entity="Department",
                level="info",
                code=200,
                message="Department Updated Successfully.",
                details={"department_id": data.id, "name": data.name},
                source="DepartmentService",
            )
            return BaseResponseDto(success=True, code=200, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="Edit",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while updating department",
                details={"error": str(ex)},
                source="DepartmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating department",
            )

    async def delete(self, data: Department | None):
        try:
            if not data or not data.id:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Department not found",
                )

            dynamic_includes = self.helper_service.generate_dynamic_includes(Department, ["users"])
            dept_res = await self.department_repository.find_one(Department.id == data.id, dynamic_includes)
            if not dept_res.success or not dept_res.data:
                await self.logger.log(
                    action="Delete",
                    entity="Department",
                    level="warning",
                    code=404,
                    message="Department Not Found for Deletion.",
                    details={"department_id": data.id},
                    source="DepartmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    message="Department not found",
                )

            department = dept_res.data
            if department.users and len(department.users) > 0:
                await self.logger.log(
                    action="Delete",
                    entity="Department",
                    level="warning",
                    code=400,
                    message="Department Cannot Be Deleted Because It Has Users Associated with It.",
                    details={"department_id": data.id, "users_count": len(department.users)},
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
                details={"error": str(ex)},
                source="DepartmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting department",
            )
