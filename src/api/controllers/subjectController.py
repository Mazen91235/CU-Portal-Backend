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
   SubjectCreateDto,SubjectUpdateDto,SubjectSearchDto,SubjectResponseDto,SubjectMinResponseDto,
)

from core.dtos.userSubjectLinkDtos import (
  UserSubjectLinkRegisterDto,UserSubjectLinkUnregisterDto,SubjectEnrolledResponseDto
)


class SubjectController(ISubjectController):
    def __init__(self, subject_service: ISubjectService,helper_service: IHelperService, logger: IBaseLogger):
        self.subject_service = subject_service
        self.helper_service = helper_service

        self.logger = logger

    # CRUD Functions
    async def create(self, request):
      try:
        await self.subject_service.begin_transaction()
        payload=await request.json()
        data=Generator[SubjectCreateDto].generate(SubjectCreateDto,payload)
        subject=Mapper[SubjectCreateDto,Subject].map(data,Subject)
        subject.details = {
            "description": data.description,
            "max_students": data.max_students,
        }
        subject.code = subject.code.strip().upper()
        response=await self.subject_service.create(subject)
        if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
        
        await self.subject_service.commit_transaction()
        return ResponseHandler.generate_response(
            success=True, code=201, message="Subject created successfully", data=SubjectResponseDto.model_validate(response.data).model_dump(mode="json"),
        )
      except Exception as e:
        await self.subject_service.rollback_transaction()
        await self.logger.log(
            action="Create",
            entity="Subject",
            level="error",
            code=500,
            message=f"An error occurred while processing the request",
            details={"error": str(e)},
            source="SubjectController",
        )
        return ResponseHandler.generate_response(
            success=False,
            code=500,
            message="An error occurred while processing the request, please try again later",
        )
    
    async def find_one(self, request):
        try:
            subject_id = request.path_params.get("subject_id")
            response = await self.subject_service.find_one(
                Subject.id == int(subject_id), includes=["faculty", "department", "year", "users"]
            )
            if not response.success:
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)
            if not response.data:
                await self.logger.log(
                    action="FindOne", entity="Subject", level="warning", code=404,
                    message="Subject not found", details={"subject_id": subject_id},
                    source="SubjectController",
                )
                return ResponseHandler.generate_response(success=False, code=404, message="Subject not found")
            return ResponseHandler.generate_response(success=True, code=200, message="Subject retrieved successfully",  data=SubjectResponseDto.model_validate(response.data).model_dump(mode="json"),)
        except Exception as e:
            await self.logger.log(
                action="FindOne", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")

    async def find(self, request):
        try:
            query_params = dict(request.query_params)
            data = Generator[SubjectSearchDto].generate(SubjectSearchDto, query_params)
            page = data.page or 1
            limit = data.limit or 50
            order_by = query_params.get("order_by") or "name"

            response = await self.subject_service.find(
                data, includes=["faculty", "department", "year", "users"],
                is_and=True, order_by=order_by, page=page, limit=limit + 1,
            )
            if not response.success:
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)

            subjects = response.data
            has_next = len(subjects) > limit
            subjects = subjects[:limit]

            if page > 1 and not subjects:
                await self.logger.log(
                    action="Find", entity="Subject", level="warning", code=400,
                    message="Invalid page number provided for subjects retrieval.",
                    details={"page": page}, source="SubjectController",
                )
                return ResponseHandler.generate_response(success=False, code=400, message="Invalid page number")

            await self.logger.log(
                action="Find", entity="Subject", level="info", code=200,
                message="Subjects retrieved successfully.",
                details={"subjects_count": len(subjects)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Subjects retrieved successfully",
                data=[SubjectResponseDto.model_validate(s).model_dump(mode="json") for s in subjects],
                next=has_next,
            )
        except Exception as e:
            await self.logger.log(
                action="Find", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")

    async def search(self, request):
        try:
            current_user = user_context.get()
            if not current_user:
                return ResponseHandler.generate_response(success=False, code=401, message="Unauthorized")

            query_params = dict(request.query_params)
            data = Generator[SubjectSearchDto].generate(SubjectSearchDto, query_params)
            page = data.page or 1
            limit = data.limit or 50

            response = await self.subject_service.search(
                current_user,
                query=data.query,
                faculty_id=data.faculty_id,
                department_id=data.department_id,
                year_id=data.year_id,
                page=page,
                limit=limit + 1,
            )
            if not response.success:
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)

            subjects = response.data
            has_next = len(subjects) > limit
            subjects = subjects[:limit]

            if page > 1 and not subjects:
                await self.logger.log(
                    action="Search", entity="Subject", level="warning", code=400,
                    message="Invalid page number provided for subjects search.",
                    details={"page": page}, source="SubjectController",
                )
                return ResponseHandler.generate_response(success=False, code=400, message="Invalid page number")

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Subjects search completed successfully",
                data=[SubjectMinResponseDto.model_validate(s).model_dump(mode="json") for s in subjects],
                next=has_next,
            )
        except Exception as e:
            await self.logger.log(
                action="Search", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")

    async def update(self, request):
        try:
            await self.subject_service.begin_transaction()
            subject_id = int(request.path_params.get("subject_id"))
            payload = await request.json()
            data = Generator[SubjectUpdateDto].generate(SubjectUpdateDto, payload)
            subject = Mapper[SubjectUpdateDto, Subject].map(data, Subject)
            subject.details = {"description": data.description, "max_students": data.max_students}

            response = await self.subject_service.update(subject_id, subject)
            if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)

            await self.subject_service.commit_transaction()
            return ResponseHandler.generate_response(success=True, code=200, message="Subject updated successfully", data=SubjectResponseDto.model_validate(response.data).model_dump(mode="json"),)
        except Exception as e:
            await self.subject_service.rollback_transaction()
            await self.logger.log(
                action="Update", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")

    async def delete(self, request):
        try:
            await self.subject_service.begin_transaction()
            subject_id = int(request.path_params.get("subject_id"))
            response = await self.subject_service.delete(subject_id)
            if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)
            await self.subject_service.commit_transaction()
            return ResponseHandler.generate_response(success=True, code=200, message="Subject deleted successfully")
        except Exception as e:
            await self.subject_service.rollback_transaction()
            await self.logger.log(
                action="Delete", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")
    
    # USER Functions
    async def register(self, request):
        try:
            await self.subject_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserSubjectLinkRegisterDto].generate(UserSubjectLinkRegisterDto, payload)

            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=user_response.code, message=user_response.message)
            user = user_response.data
            if not user:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=401, message="Unauthorized")

            response = await self.subject_service.register(user.id, data.subject_id)
            if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)

            await self.subject_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Registered to course successfully",
                data=SubjectEnrolledResponseDto.model_validate(response.data).model_dump(mode="json"),
            )
        except Exception as e:
            await self.subject_service.rollback_transaction()
            await self.logger.log(
                action="Register", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")

    async def unregister(self, request):
        try:
            await self.subject_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserSubjectLinkUnregisterDto].generate(UserSubjectLinkUnregisterDto, payload)

            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=user_response.code, message=user_response.message)
            user = user_response.data
            if not user:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=401, message="Unauthorized")

            response = await self.subject_service.unregister(user.id, data.subject_id)
            if not response.success:
                await self.subject_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)

            await self.subject_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Unregistered from course successfully",
                data=SubjectEnrolledResponseDto.model_validate(response.data).model_dump(mode="json"),
            )
        except Exception as e:
            await self.subject_service.rollback_transaction()
            await self.logger.log(
                action="Unregister", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")

    async def get_enrolled(self, request):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return ResponseHandler.generate_response(success=False, code=user_response.code, message=user_response.message)
            user = user_response.data
            if not user:
                return ResponseHandler.generate_response(success=False, code=401, message="Unauthorized")

            response = await self.subject_service.get_enrolled(user.id)
            if not response.success:
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Enrolled courses retrieved successfully",
                data=[SubjectEnrolledResponseDto.model_validate(s).model_dump(mode="json") for s in response.data],
            )
        except Exception as e:
            await self.logger.log(
                action="GetEnrolled", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")

    async def get_available(self, request):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return ResponseHandler.generate_response(success=False, code=user_response.code, message=user_response.message)
            user = user_response.data
            if not user:
                return ResponseHandler.generate_response(success=False, code=401, message="Unauthorized")

            query_params = dict(request.query_params)
            query = query_params.get("query", "").strip() or None

            response = await self.subject_service.get_available(user.id, query=query)
            if not response.success:
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Available courses retrieved successfully",
                data=[SubjectEnrolledResponseDto.model_validate(s).model_dump(mode="json") for s in response.data],
            )
        except Exception as e:
            await self.logger.log(
                action="GetAvailable", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")
        
    async def search_registered(self, request):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return ResponseHandler.generate_response(success=False, code=user_response.code, message=user_response.message)
            current_user = user_response.data
            if not current_user:
                return ResponseHandler.generate_response(success=False, code=401, message="Unauthorized")

            query_params = dict(request.query_params)
            data = Generator[SubjectSearchDto].generate(SubjectSearchDto, query_params)
            page = data.page or 1
            limit = data.limit or 50

            response = await self.subject_service.search_registered(
                current_user.id, query=data.query, page=page, limit=limit + 1
            )
            if not response.success:
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)

            subjects = response.data
            has_next = len(subjects) > limit
            subjects = subjects[:limit]

            if page > 1 and not subjects:
                return ResponseHandler.generate_response(success=False, code=400, message="Invalid page number")

            return ResponseHandler.generate_response(
                success=True, code=200, message="Registered courses search completed successfully",
                data=[SubjectMinResponseDto.model_validate(s).model_dump(mode="json") for s in subjects],
                next=has_next,
            )
        except Exception as e:
            await self.logger.log(
                action="Search", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")

    async def get_enrolled_one(self, request):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return ResponseHandler.generate_response(success=False, code=user_response.code, message=user_response.message)
            current_user = user_response.data
            if not current_user:
                return ResponseHandler.generate_response(success=False, code=401, message="Unauthorized")

            subject_id = int(request.path_params.get("subject_id"))
            response = await self.subject_service.get_enrolled_one(current_user.id, subject_id)
            if not response.success:
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)

            return ResponseHandler.generate_response(
                success=True, code=200, message="Enrolled course retrieved successfully",
                data=SubjectEnrolledResponseDto.model_validate(response.data).model_dump(mode="json"),
            )
        except Exception as e:
            await self.logger.log(
                action="GetEnrolledOne", entity="Subject", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="SubjectController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")