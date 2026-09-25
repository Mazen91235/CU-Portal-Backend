from typing import cast
from core.iControllers.iExamController import IExamController
from core.iServices.iExamService import IExamService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.task import Task
from core.dtos.examDtos import (
    ExamCreateDto,
    ExamUpdateDto,
    ExamResponseDto,
    ExamSearchDto,
    ExamDeleteDto,
)


class ExamController(IExamController):
    def __init__(self, exam_service: IExamService, logger: IBaseLogger):
        self.exam_service = exam_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[ExamSearchDto].generate(
                ExamSearchDto, {"id": id}
            )

            response = await self.exam_service.find_one(
                entity_search_dto,
                [
                    "author",
                    "subject.faculty",
                    "subject.department",
                    "subject.year",
                ],
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            exam = response.data

            if not exam:
                await self.logger.log(
                    action="FindOne",
                    entity="Exam",
                    level="info",
                    code=404,
                    message="Exam not found",
                    source="ExamController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Exam not found",
                )

            exam_mapped = Mapper[Task, ExamResponseDto].map(exam, ExamResponseDto, True)

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=exam_mapped,
            )

        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Exam",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ExamController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[ExamSearchDto].generate_from_query(
                ExamSearchDto, query
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

            response = await self.exam_service.find(
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

            exams = response.data

            exams_mapped = Mapper[Task, ExamResponseDto].map_list(
                exams or [], ExamResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=exams_mapped,
                next_page=response.next_page,
            )

        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Exam",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ExamController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            exam = Mapper[ExamCreateDto, Task].map(data, Task)

            response = await self.exam_service.create(exam)

            if not response.success:
                await self.exam_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            created_exam = response.data
            if not created_exam:
                await self.exam_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="Failed to create exam",
                    details={},
                    source="ExamController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create exam",
                )

            exam_mapped = Mapper[Task, ExamResponseDto].map(
                created_exam, ExamResponseDto, True
            )

            await self.exam_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=exam_mapped,
                message="Exam created successfully",
            )

        except Exception as e:
            await self.exam_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Exam",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ExamController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, id, data):
        try:
            exam = cast(
                Task,
                Mapper[ExamUpdateDto, Task].map(data, Task),
            )
            exam.id = id

            response = await self.exam_service.update(exam)

            if not response.success:
                await self.exam_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_exam = response.data
            if not updated_exam:
                await self.exam_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="Failed to update exam",
                    details={},
                    source="ExamController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to update exam",
                )
            exam_mapped = Mapper[Task, ExamResponseDto].map(
                updated_exam, ExamResponseDto, True
            )

            await self.exam_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=exam_mapped,
                message="Exam updated successfully",
            )

        except Exception as e:
            await self.exam_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Exam",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ExamController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            data = Generator[ExamDeleteDto].generate(ExamDeleteDto, {"id": id})
            entity = Mapper[ExamDeleteDto, Task].map(data, Task)

            response = await self.exam_service.delete(entity)

            if not response.success:
                await self.exam_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.exam_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Exam deleted successfully",
            )

        except Exception as e:
            await self.exam_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Exam",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ExamController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
