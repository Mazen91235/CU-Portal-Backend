from core.iControllers.iFacultyController import IFacultyController
from core.iServices.iFacultyService import IFacultyService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser

# Entities & DTOs
from core.entities.faculty import Faculty
from core.dtos.facultyDtos import (
    FacultyCreateDto,
    FacultyResponseDto,
    FacultyUpdateDto,
    FacultySearchDto,
)
from core.models.queryModel import QueryModel


class FacultyController(IFacultyController):
    def __init__(self, faculty_service: IFacultyService, logger: IBaseLogger):
        self.faculty_service = faculty_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request):
        try:
            faculty_id = request.path_params.get("faculty_id")
            if not faculty_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Faculty ID is required",
                )
            entity_search_dto = Generator[FacultySearchDto].generate(
                FacultySearchDto, {"id": faculty_id}
            )
            response = await self.faculty_service.find_one(entity_search_dto)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            faculty = response.data
            if not faculty:
                await self.logger.log(
                    action="FindOne",
                    entity="Faculty",
                    level="info",
                    code=404,
                    message="Faculty not found",
                    source="FacultyController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Faculty not found",
                )
            faculty_mapped = Mapper[Faculty, FacultyResponseDto].map(
                faculty, FacultyResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=faculty_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="FacultyController",
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
                QueryModel[FacultySearchDto],
            )
            entity_search_dto = Generator[FacultySearchDto].generate_from_query(
                FacultySearchDto, query
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

            response = await self.faculty_service.find(
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

            faculties = response.data
            if not faculties:
                await self.logger.log(
                    action="Find",
                    entity="Faculty",
                    level="info",
                    code=404,
                    message="Faculties not found",
                    source="FacultyController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Faculties not found",
                )

            faculties_mapped = Mapper[Faculty, FacultyResponseDto].map_list(
                faculties, FacultyResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=faculties_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request):
        try:
            await self.faculty_service.begin_transaction()
            payload = await request.json()
            data = Generator[FacultyCreateDto].generate(FacultyCreateDto, payload)
            faculty = Mapper[FacultyCreateDto, Faculty].map(data, Faculty)
            response = await self.faculty_service.create(faculty)
            if not response.success:
                await self.faculty_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            created_faculty = response.data
            faculty_mapped = Mapper[Faculty, FacultyResponseDto].map(
                created_faculty, FacultyResponseDto, True
            )
            await self.faculty_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=faculty_mapped,
                message="Faculty created successfully",
            )
        except Exception as e:
            await self.faculty_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request):
        try:
            await self.faculty_service.begin_transaction()
            faculty_id = request.path_params.get("faculty_id")
            if not faculty_id:
                await self.faculty_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Faculty ID is required",
                )

            payload = await request.json()
            data = Generator[FacultyUpdateDto].generate(FacultyUpdateDto, payload)
            faculty = Mapper[FacultyUpdateDto, Faculty].map(data, Faculty)
            faculty.id = int(faculty_id)

            response = await self.faculty_service.update(faculty)
            if not response.success:
                await self.faculty_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_faculty = response.data
            faculty_mapped = Mapper[Faculty, FacultyResponseDto].map(
                updated_faculty, FacultyResponseDto, True
            )
            await self.faculty_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=faculty_mapped,
                message="Faculty updated successfully",
            )
        except Exception as e:
            await self.faculty_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request):
        try:
            await self.faculty_service.begin_transaction()
            faculty_id = request.path_params.get("faculty_id")
            if not faculty_id:
                await self.faculty_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Faculty ID is required",
                )

            entity = Faculty(id=int(faculty_id))
            response = await self.faculty_service.delete(entity)
            if not response.success:
                await self.faculty_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.faculty_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Faculty deleted successfully",
            )
        except Exception as e:
            await self.faculty_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    # Additional Query Functions
    async def search(self, request):
        try:
            query_param = request.query_params.get("query", "")
            query = Parser.parse_query(
                request.query_params.get("query", "{}"),
                QueryModel[FacultySearchDto],
            )
            entity_search_dto = Generator[FacultySearchDto].generate_from_query(
                FacultySearchDto, query
            )
            if not entity_search_dto.query and query_param:
                entity_search_dto.query = query_param

            includes = query.includes
            selects = query.selects
            is_and = query.is_and
            starts_with = True
            is_exact = False
            order_by = ["name"]
            descending = False
            page = query.page or 1
            limit = query.limit or 50

            response = await self.faculty_service.find(
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

            faculties = response.data
            if not faculties:
                await self.logger.log(
                    action="Search",
                    entity="Faculty",
                    level="info",
                    code=404,
                    message="Faculties not found",
                    source="FacultyController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Faculties not found",
                )

            faculties_mapped = Mapper[Faculty, FacultyResponseDto].map_list(
                faculties, FacultyResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=faculties_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Search",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
