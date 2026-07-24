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
from core.utils.parser import Parser


class DepartmentController(IDepartmentController):
    def __init__(self, department_service: IDepartmentService, logger: IBaseLogger):
        self.department_service = department_service
        self.logger = logger

    async def find_one(self, request):
        try:
            department_id = request.path_params.get("department_id")
            if not department_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Department ID is required",
                )
            entity_search_dto = Generator[DepartmentSearchDto].generate(
                DepartmentSearchDto, {"id": department_id}
            )
            response = await self.department_service.find_one(
                entity_search_dto,
                ["faculty", "users", "subjects", "tasks", "announcements"],
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
            summary_data = {
                "users": len(department.users) if department.users else 0,
                "subjects": len(department.subjects) if department.subjects else 0,
                "tasks": len([t for t in department.tasks if t.type.lower() != "exam"]) if department.tasks else 0,
                "exams": len([t for t in department.tasks if t.type.lower() == "exam"]) if department.tasks else 0,
                "announcements": len(department.announcements) if department.announcements else 0,
                "events": 0,
            }
            department_mapped = Mapper[Department, DepartmentResponseDto].map(
                department, DepartmentResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data={
                    "department": department_mapped,
                    "summary": summary_data,
                },
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="DepartmentController",
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
                QueryModel[DepartmentSearchDto],
            )
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
                details={"error": str(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def search(self, request):
        try:
            query_params = request.query_params
            query_val = query_params.get("query", "").strip()
            faculty_id = query_params.get("faculty_id")
            study_type = query_params.get("study_type", "").strip().title()

            payload = {}
            if query_val:
                payload["query"] = query_val
            if faculty_id:
                payload["faculty_id"] = int(faculty_id) if str(faculty_id).isdigit() else None
            if study_type:
                payload["study_type"] = study_type

            entity_search_dto = Generator[DepartmentSearchDto].generate(
                DepartmentSearchDto, payload
            )
            response = await self.department_service.find(
                entity_search_dto,
                None,
                None,
                False,
                True,
                False,  # case-insensitive starts_with or contains search
                ["name"],
                False,
                1,
                50,
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            departments = response.data
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
                action="Search",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while processing the search",
                details={"error": str(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request):
        try:
            await self.department_service.begin_transaction()
            payload = await request.json()
            data = Generator[DepartmentCreateDto].generate(DepartmentCreateDto, payload)
            department = Mapper[DepartmentCreateDto, Department].map(data, Department)
            response = await self.department_service.create(department)
            if not response.success:
                await self.department_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.department_service.commit_transaction()
            dept_mapped = Mapper[Department, DepartmentResponseDto].map(
                response.data, DepartmentResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=dept_mapped,
            )
        except Exception as e:
            await self.department_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request):
        try:
            await self.department_service.begin_transaction()
            department_id = request.path_params.get("department_id")
            if not department_id:
                await self.department_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Department ID is required",
                )
            payload = await request.json()
            data = Generator[DepartmentUpdateDto].generate(DepartmentUpdateDto, payload)
            department = Mapper[DepartmentUpdateDto, Department].map(data, Department)
            department.id = int(department_id)
            response = await self.department_service.update(department)
            if not response.success:
                await self.department_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.department_service.commit_transaction()
            dept_mapped = Mapper[Department, DepartmentResponseDto].map(
                response.data, DepartmentResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=dept_mapped,
            )
        except Exception as e:
            await self.department_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Department",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request):
        try:
            await self.department_service.begin_transaction()
            department_id = request.path_params.get("department_id")
            if not department_id:
                await self.department_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Department ID is required",
                )
            department = Department()
            department.id = int(department_id)
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
                details={"error": str(e)},
                source="DepartmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
