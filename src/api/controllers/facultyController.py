from typing import cast
from core.iControllers.iFacultyController import IFacultyController
from core.iServices.iFacultyService import IFacultyService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.faculty import Faculty
from core.dtos.facultyDtos import (
    FacultyCreateDto,
    FacultyResponseDto,
    FacultyUpdateDto,
    FacultySearchDto,
    FacultyDeleteDto,
)
from core.models.queryModel import QueryModel


class FacultyController(IFacultyController):
    def __init__(self, faculty_service: IFacultyService, logger: IBaseLogger):
        self.faculty_service = faculty_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[FacultySearchDto].generate(
                FacultySearchDto, {"id": id}
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
                details={"error": repr(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
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
            faculties_mapped = Mapper[Faculty, FacultyResponseDto].map_list(
                faculties or [], FacultyResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=faculties_mapped,
                next_page=response.next_page
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Faculty",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.faculty_service.begin_transaction()
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
            if not created_faculty:
                await self.faculty_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Faculty",
                    level="error",
                    code=500,
                    message="Failed to create faculty",
                    source="FacultyController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create faculty, Please try again later",
                )
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
                details={"error": repr(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, id, data):
        try:
            await self.faculty_service.begin_transaction()
            faculty = cast(
                Faculty,
                Mapper[FacultyUpdateDto, Faculty].map(data, Faculty),
            )
            faculty.id = id

            response = await self.faculty_service.update(faculty)
            if not response.success:
                await self.faculty_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_faculty = response.data
            if not updated_faculty:
                await self.faculty_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Faculty",
                    level="error",
                    code=500,
                    message="Failed to update faculty",
                    source="FacultyController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to update faculty, Please try again later",
                )
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
                details={"error": repr(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            await self.faculty_service.begin_transaction()
            data = Generator[FacultyDeleteDto].generate(FacultyDeleteDto, {"id": id})
            entity = Mapper[FacultyDeleteDto, Faculty].map(data, Faculty)
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
                details={"error": repr(e)},
                source="FacultyController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
