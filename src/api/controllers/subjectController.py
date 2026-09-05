from typing import cast
from core.iControllers.iSubjectController import ISubjectController
from core.iServices.iSubjectService import ISubjectService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from business.contextVars.userContext import user_context

# Entities & DTOs
from core.entities.subject import Subject
from core.dtos.subjectDtos import (
    SubjectCreateDto,
    SubjectUpdateDto,
    SubjectSearchDto,
    SubjectResponseDto,
)


class SubjectController(ISubjectController):
    def __init__(
        self,
        subject_service: ISubjectService,
        helper_service: IHelperService,
        logger: IBaseLogger,
    ):
        self.subject_service = subject_service
        self.helper_service = helper_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[SubjectSearchDto].generate(
                SubjectSearchDto, {"id": id}
            )
            response = await self.subject_service.find_one(
                entity_search_dto,
                includes=["faculty", "department", "year", "user_subject_links.user"],
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )

            subject = response.data
            if not subject:
                await self.logger.log(
                    action="FindOne",
                    entity="Subject",
                    level="info",
                    code=404,
                    message="Subject not found",
                    source="SubjectController",
                )
                return ResponseHandler.generate_response(
                    success=False, code=404, message="Subject not found"
                )

            subject_mapped = Mapper[Subject, SubjectResponseDto].map(
                subject, SubjectResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Subject retrieved successfully",
                data=subject_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[SubjectSearchDto].generate_from_query(
                SubjectSearchDto, query
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

            response = await self.subject_service.find(
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
                    success=False, code=response.code, message=response.message
                )

            subjects = response.data

            subjects_mapped = Mapper[Subject, SubjectResponseDto].map_list(
                subjects or [], SubjectResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Subjects retrieved successfully",
                data=subjects_mapped,
                next_page=response.next_page,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.subject_service.begin_transaction()
            subject = Mapper[SubjectCreateDto, Subject].map(data, Subject)
            response = await self.subject_service.create(subject)
            if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            created_subject = response.data
            if not created_subject:
                await self.subject_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Subject",
                    level="error",
                    code=500,
                    message="Failed to create subject",
                    source="SubjectController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            created_subject_mapped = Mapper[Subject, SubjectResponseDto].map(
                created_subject, SubjectResponseDto, True
            )

            await self.subject_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                message="Subject created successfully",
                data=created_subject_mapped,
            )

        except Exception as e:
            await self.subject_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Subject",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, id, data):
        try:
            await self.subject_service.begin_transaction()
            subject = cast(
                Subject, Mapper[SubjectUpdateDto, Subject].map(data, Subject)
            )
            subject.id = id
            response = await self.subject_service.update(subject)
            if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )
            subject = response.data
            if not subject:
                await self.subject_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Subject",
                    level="error",
                    code=500,
                    message="Failed to update subject",
                    source="SubjectController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            subject_mapped = Mapper[Subject, SubjectResponseDto].map(
                subject, SubjectResponseDto, True
            )
            await self.subject_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Subject updated successfully",
                data=subject_mapped,
            )
        except Exception as e:
            await self.subject_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            await self.subject_service.begin_transaction()
            subject = Generator[Subject].generate(Subject, {"id": id})
            response = await self.subject_service.delete(subject)
            if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )
            await self.subject_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True, code=200, message="Subject deleted successfully"
            )
        except Exception as e:
            await self.subject_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    # Subject Specific Functions
    async def get_available(self, request):
        try:
            response = await self.subject_service.get_available()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )

            available_subjects = response.data or []
            subjects_mapped = Mapper[Subject, SubjectResponseDto].map_list(
                available_subjects, SubjectResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Available courses retrieved successfully",
                data=subjects_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="GetAvailable",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_enrolled(self, request):
        try:
            response = await self.subject_service.get_enrolled()
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )

            enrolled_subjects = response.data
            if not enrolled_subjects:
                await self.logger.log(
                    action="GetEnrolled",
                    entity="Subject",
                    level="error",
                    code=500,
                    message="Failed to retrieve enrolled subjects",
                    source="SubjectController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            subjects_mapped = Mapper[Subject, SubjectResponseDto].map_list(
                enrolled_subjects, SubjectResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Enrolled courses retrieved successfully",
                data=subjects_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="GetEnrolled",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_enrolled_one(self, request, id):
        try:
            response = await self.subject_service.get_enrolled_one(id)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )

            enrolled_subject = response.data
            if not enrolled_subject:
                await self.logger.log(
                    action="GetEnrolledOne",
                    entity="Subject",
                    level="warning",
                    code=404,
                    message="Enrolled course not found",
                    details={"subject_id": id},
                    source="SubjectController",
                )
                return ResponseHandler.generate_response(
                    success=False, code=404, message="Enrolled course not found"
                )

            subject_mapped = Mapper[Subject, SubjectResponseDto].map(
                enrolled_subject, SubjectResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Enrolled course retrieved successfully",
                data=subject_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="GetEnrolledOne",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def register(self, request, data):
        try:
            await self.subject_service.begin_transaction()
            response = await self.subject_service.register(data.subject_id)
            if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )

            await self.subject_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Registered to course successfully",
            )
        except Exception as e:
            await self.subject_service.rollback_transaction()
            await self.logger.log(
                action="Register",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def unregister(self, request, data):
        try:
            await self.subject_service.begin_transaction()
            response = await self.subject_service.unregister(data.subject_id)
            if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )

            await self.subject_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Unregistered from course successfully",
            )
        except Exception as e:
            await self.subject_service.rollback_transaction()
            await self.logger.log(
                action="Unregister",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
