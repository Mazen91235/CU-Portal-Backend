from typing import cast
from core.iControllers.iDepartmentController import IDepartmentController
from core.iServices.iDepartmentService import IDepartmentService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.entities.department import Department
from core.dtos.departmentDtos import (
    DepartmentCreateDto,
    DepartmentUpdateDto,
    DepartmentSearchDto,
    DepartmentResponseDto,
)
from core.models.queryModel import QueryModel
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler


class DepartmentController(IDepartmentController):
    def __init__(self, department_service: IDepartmentService, logger: IBaseLogger):
        self.department_service = department_service
        self.logger = logger

    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[DepartmentSearchDto].generate(
                DepartmentSearchDto, {"id": id}
            )
            response = await self.department_service.find_one(
                entity_search_dto,
                ["faculty", "users", "subjects"],
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            department = response.data
            if not department:
                await self.logger.log(
                    action="FindOne",
                    entity="Department",
                    level="info",
                    code=404,
                    message="Department not found",
                    source="DepartmentController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Department not found",
                )
            department_mapped = Mapper[Department, DepartmentResponseDto].map(
                department, DepartmentResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=department_mapped,
                message="Department found successfully",
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[DepartmentSearchDto].generate_from_query(
                DepartmentSearchDto, query
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

            response = await self.department_service.find(
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

            departments = response.data
            if not departments:
                await self.logger.log(
                    action="Find",
                    entity="Department",
                    level="info",
                    code=404,
                    message="Departments not found",
                    source="DepartmentController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Departments not found",
                )

            departments_mapped = Mapper[Department, DepartmentResponseDto].map_list(
                departments, DepartmentResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=departments_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.department_service.begin_transaction()
            department = Mapper[DepartmentCreateDto, Department].map(data, Department)
            response = await self.department_service.create(department)
            if not response.success:
                await self.department_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            department_mapped = Mapper[Department, DepartmentResponseDto].map(
                response.data, DepartmentResponseDto, True
            )
            await self.department_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=department_mapped,
            )
        except Exception as e:
            await self.department_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, id, data):
        try:
            await self.department_service.begin_transaction()
            department = cast(
                Department,
                Mapper[DepartmentUpdateDto, Department].map(data, Department),
            )
            department.id = id
            response = await self.department_service.update(department)
            if not response.success:
                await self.department_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            department_mapped = Mapper[Department, DepartmentResponseDto].map(
                response.data, DepartmentResponseDto, True
            )
            await self.department_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=department_mapped,
            )
        except Exception as e:
            await self.department_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            await self.department_service.begin_transaction()
            department = Generator[Department].generate(Department, {"id": id})
            response = await self.department_service.delete(department)
            if not response.success:
                await self.department_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.department_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Department deleted successfully",
            )
        except Exception as e:
            await self.department_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
