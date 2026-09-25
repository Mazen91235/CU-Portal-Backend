from sqlalchemy import func, and_, or_
from typing import cast
from core.iServices.iSubjectService import ISubjectService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.subject import Subject
from core.entities.userSubjectLink import UserSubjectLink
from core.entities.year import Year
from core.dtos.baseDtos import BaseResponseDto
from core.utils.cachingHandler import caching_handler


class SubjectService(ISubjectService):
    def __init__(
        self,
        subject_repository: IBaseRepository[Subject],
        user_subject_link_repository: IBaseRepository[UserSubjectLink],
        year_repository: IBaseRepository[Year],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.subject_repository = subject_repository
        self.user_subject_link_repository = user_subject_link_repository
        self.year_repository = year_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.subject_repository.begin_transaction()

    async def commit_transaction(self):
        await self.subject_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.subject_repository.rollback_transaction()

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
                Subject, data, ["name", "code"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Subject, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Subject", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Subject", order_by, descending
            )
            result = await self.subject_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False, code=result.code, data=None, message=result.message
                )
            return BaseResponseDto(success=True, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while finding subject",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding subject",
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
            if not data or data.user_id is None:
                predicate = self.helper_service.generate_dynamic_predicate(
                    Subject, data, ["name", "code"], is_and, starts_with, is_exact
                )
                dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Subject, includes
                )
                dynamic_selects = self.helper_service.generate_dynamic_selects(
                    "Subject", selects
                )
                dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                    "Subject", order_by, descending
                )
                result = await self.subject_repository.find(
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
                return BaseResponseDto(
                    success=True, data=result.data, next_page=result.next_page
                )
            else:
                dynamic_includes = self.helper_service.generate_dynamic_includes(
                    UserSubjectLink,
                    [
                        "subject.faculty",
                        "subject.department",
                        "subject.year",
                        "subject.users",
                    ],
                )
                subject_link_response = await self.user_subject_link_repository.find(
                    UserSubjectLink.user_id == data.user_id, dynamic_includes
                )
                if not subject_link_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=subject_link_response.code,
                        data=None,
                        message=subject_link_response.message,
                    )
                subject_links = subject_link_response.data
                if not subject_links:
                    return BaseResponseDto(
                        success=True, data=[], next_page=subject_link_response.next_page
                    )
                subjects = [link.subject for link in subject_links if link.subject]
                return BaseResponseDto(
                    success=True,
                    data=subjects,
                    next_page=subject_link_response.next_page,
                )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while finding subjects",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding subjects",
            )

    async def create(self, data):
        try:
            data.faculty_id = int(data.faculty_id or "")
            data.department_id = int(data.department_id or "")
            data.year_id = int(data.year_id or "")
            data.code = data.code.strip().upper()
            existing_subject_response = await self.subject_repository.find_one(
                and_(
                    Subject.faculty_id == data.faculty_id,
                    Subject.department_id == data.department_id,
                    Subject.year_id == data.year_id,
                    or_(
                        func.lower(Subject.code) == data.code.lower(),
                        func.lower(Subject.name) == data.name.lower(),
                    ),
                )
            )

            if not existing_subject_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_subject_response.code,
                    data=None,
                    message=existing_subject_response.message,
                )

            existing_subject = existing_subject_response.data
            if existing_subject:
                await self.logger.log(
                    action="Create",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="Subject with this name or code already exists in the specified faculty, department and year.",
                    details={
                        "faculty_id": data.faculty_id,
                        "department_id": data.department_id,
                        "year_id": data.year_id,
                        "code": data.code,
                        "name": data.name,
                    },
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Subject with this name or code already exists in the specified criteria",
                )

            restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id,
                    department_id=data.department_id,
                    year_id=data.year_id,
                )
            )
            if not restricted_access_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="User does not have access to the specified faculty, department or year.",
                    details={
                        "faculty_id": data.faculty_id,
                        "department_id": data.department_id,
                        "year_id": data.year_id,
                    },
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=restricted_access_response.code,
                    data=None,
                    message=restricted_access_response.message,
                )

            create_response = await self.subject_repository.create(data)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )

            created_subject = create_response.data
            if not created_subject:
                await self.logger.log(
                    action="Create",
                    entity="Subject",
                    level="error",
                    code=500,
                    message="Failed to create subject.",
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to create subject",
                )
            await self.logger.log(
                action="Create",
                entity="Subject",
                level="info",
                code=201,
                message="Subject Created Successfully.",
                source="SubjectService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_subject,
                message="Subject created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while creating subject",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating subject",
            )

    async def update(self, data):
        try:
            existing_response = await self.subject_repository.find_one(
                Subject.id == data.id
            )
            if not existing_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_response.code,
                    data=None,
                    message=existing_response.message,
                )

            subject = existing_response.data
            if not subject:
                await self.logger.log(
                    action="Update",
                    entity="Subject",
                    level="warning",
                    code=404,
                    message="Subject not found for update",
                    details={"subject_id": data.id},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Subject not found"
                )
            data.faculty_id = int(data.faculty_id or "")
            data.department_id = int(data.department_id or "")
            data.year_id = int(data.year_id or "")
            data.code = data.code.strip().upper()
            duplicate_response = await self.subject_repository.find_one(
                and_(
                    Subject.faculty_id == subject.faculty_id,
                    Subject.department_id == subject.department_id,
                    Subject.year_id == subject.year_id,
                    or_(
                        func.lower(Subject.code) == data.code.lower(),
                        func.lower(Subject.name) == data.name.lower(),
                    ),
                )
            )
            if not duplicate_response.success:
                return BaseResponseDto(
                    success=False,
                    code=duplicate_response.code,
                    data=None,
                    message=duplicate_response.message,
                )

            duplicate = duplicate_response.data
            if duplicate and duplicate.id != subject.id:
                await self.logger.log(
                    action="Update",
                    entity="Subject",
                    level="warning",
                    code=404,
                    message="Subject with this code Already Exists in the Specified Faculty, Department and Year for Subject Update",
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Subject with this code already exists in the specified criteria",
                )

            restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=subject.faculty_id,
                    department_id=subject.department_id,
                    year_id=subject.year_id,
                )
            )

            if not restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="User does not have access to the specified faculty, department or year for subject update.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=restricted_access_response.code,
                    data=None,
                    message=restricted_access_response.message,
                )

            restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id,
                    department_id=data.department_id,
                    year_id=data.year_id,
                )
            )

            if not restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="User does not have access to the specified faculty, department or year for subject update.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=restricted_access_response.code,
                    data=None,
                    message=restricted_access_response.message,
                )

            subject.name = data.name
            subject.code = data.code
            subject.faculty_id = data.faculty_id
            subject.department_id = data.department_id
            subject.year_id = data.year_id
            subject.credits = data.credits
            subject.details = data.details

            update_response = await self.subject_repository.update(subject)
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )

            updated_subject = update_response.data
            if not updated_subject:
                await self.logger.log(
                    action="Update",
                    entity="Subject",
                    level="error",
                    code=500,
                    message="Failed to update subject.",
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    message="Failed to update subject",
                )

            await self.logger.log(
                action="Update",
                entity="Subject",
                level="info",
                code=200,
                message="Subject updated successfully.",
                source="SubjectService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_subject,
                message="Subject updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while updating subject",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating subject",
            )

    async def delete(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Subject, ["user_subject_links.user"]
            )
            existing_response = await self.subject_repository.find_one(
                Subject.id == data.id, dynamic_includes
            )
            if not existing_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_response.code,
                    data=None,
                    message=existing_response.message,
                )
            subject = existing_response.data
            if not subject:
                await self.logger.log(
                    action="Delete",
                    entity="Subject",
                    level="warning",
                    code=404,
                    message="Subject not found for deletion",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Subject not found"
                )

            if subject.users and len(subject.users) > 0:
                await self.logger.log(
                    action="Delete",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="Subject cannot be deleted because it has users associated with it.",
                    details={
                        "users_count": len(subject.users),
                    },
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Subject cannot be deleted because it has users associated with it",
                )

            delete_response = await self.subject_repository.delete(subject)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )

            await self.logger.log(
                action="Delete",
                entity="Subject",
                level="info",
                code=200,
                message="Subject deleted successfully.",
                details={},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Subject deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while deleting subject",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting subject",
            )

    # Subject Specific Functions
    async def get_available(self, data):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="GetAvailable",
                    entity="Subject",
                    level="warning",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to retrieve logged in user for available courses. : {logged_in_user_response.message}",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="GetAvailable",
                    entity="Subject",
                    level="warning",
                    code=401,
                    message="Unauthorized access attempt to get available courses.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=401, data=None, message="Unauthorized"
                )
            if not data.department_id or not data.year_id:
                return BaseResponseDto(
                    success=True,
                    code=200,
                    data=[],
                    message="Department ID and Year ID are required to fetch available courses.",
                )
            response = await self.subject_repository.execute_stored_function(
                "get_user_available_subjects",
                {
                    "p_user_id": logged_in_user.id,
                    "p_department_id": data.department_id,
                    "p_year_id": data.year_id,
                    "p_query": data.query or "",
                },
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                )
            available_courses = response.data or []
            available_courses = cast(list[Subject], available_courses)
            await self.logger.log(
                action="GetAvailable",
                entity="Subject",
                level="info",
                code=200,
                message="Available courses retrieved successfully.",
                source="SubjectService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=available_courses,
                message="Available courses retrieved successfully.",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetAvailable",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while getting available courses",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while getting available courses",
            )

    async def get_enrolled(self):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="GetEnrolled",
                    entity="Subject",
                    level="warning",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to retrieve logged in user for enrolled courses. : {logged_in_user_response.message}",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="GetEnrolled",
                    entity="Subject",
                    level="warning",
                    code=401,
                    message="Unauthorized access attempt to get enrolled courses.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=401, data=None, message="Unauthorized"
                )

            dynamic_includes = self.helper_service.generate_dynamic_includes(
                UserSubjectLink,
                [
                    "subject.faculty",
                    "subject.department",
                    "subject.year",
                    "subject.users",
                ],
            )

            result = await self.user_subject_link_repository.find(
                UserSubjectLink.user_id == logged_in_user.id,
                dynamic_includes,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False, code=result.code, data=None, message=result.message
                )
            links = result.data or []
            subjects = [link.subject for link in links if link.subject]
            await self.logger.log(
                action="Get",
                entity="Subject",
                level="info",
                code=200,
                message="User Enrolled Courses Retrieved Successfully.",
                source="SubjectService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=subjects,
                message="Enrolled courses retrieved successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetEnrolled",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while getting enrolled courses",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while getting enrolled courses",
            )

    async def get_enrolled_one(self, subject_id):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="GetEnrolledOne",
                    entity="Subject",
                    level="warning",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to retrieve logged in user for enrolled course. : {logged_in_user_response.message}",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="GetEnrolledOne",
                    entity="Subject",
                    level="warning",
                    code=401,
                    message="Unauthorized access attempt to get enrolled course.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=401, data=None, message="Unauthorized"
                )

            dynamic_includes = self.helper_service.generate_dynamic_includes(
                UserSubjectLink,
                [
                    "subject.faculty",
                    "subject.department",
                    "subject.year",
                    "subject.users",
                ],
            )

            link_response = await self.user_subject_link_repository.find_one(
                and_(
                    UserSubjectLink.user_id == logged_in_user.id,
                    UserSubjectLink.subject_id == subject_id,
                ),
                dynamic_includes,
            )
            if not link_response.success:
                return BaseResponseDto(
                    success=False,
                    code=link_response.code,
                    data=None,
                    message=link_response.message,
                )
            link = link_response.data
            if not link:
                await self.logger.log(
                    action="GetEnrolledOne",
                    entity="Subject",
                    level="warning",
                    code=404,
                    message="Enrolled course not found for user.",
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Enrolled course not found",
                )
            subject = link.subject
            await self.logger.log(
                action="GetEnrolledOne",
                entity="Subject",
                level="info",
                code=200,
                message="User Enrolled Course Retrieved Successfully.",
                source="SubjectService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=subject,
                message="Enrolled course retrieved successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetEnrolledOne",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while getting enrolled course",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while retrieving enrolled course",
            )

    async def register(self, subject_id):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Register",
                    entity="Subject",
                    level="warning",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to retrieve logged in user for course registration. : {logged_in_user_response.message}",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Register",
                    entity="Subject",
                    level="warning",
                    code=401,
                    message="Unauthorized access attempt to register for course.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=401, data=None, message="Unauthorized"
                )

            subject_response = await self.subject_repository.find_one(
                Subject.id == subject_id,
            )
            if not subject_response.success:
                return BaseResponseDto(
                    success=False,
                    code=subject_response.code,
                    data=None,
                    message=subject_response.message,
                )
            subject = subject_response.data
            if not subject:
                await self.logger.log(
                    action="Register",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="Subject Not Found for Registration.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Subject not found"
                )
            logged_in_user_year_response = await self.year_repository.find_one(
                Year.id == logged_in_user.year_id
            )
            if not logged_in_user_year_response.success:
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_year_response.code,
                    data=None,
                    message=logged_in_user_year_response.message,
                )
            logged_in_user_year = logged_in_user_year_response.data
            if not logged_in_user_year:
                await self.logger.log(
                    action="Register",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="Logged in user's year not found for registration.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Your academic year information is missing. Please contact support.",
                )
            subject_year_response = await self.year_repository.find_one(
                Year.id == subject.year_id
            )
            if not subject_year_response.success:
                return BaseResponseDto(
                    success=False,
                    code=subject_year_response.code,
                    data=None,
                    message=subject_year_response.message,
                )
            subject_year = subject_year_response.data
            if not subject_year:
                await self.logger.log(
                    action="Register",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="Subject's year not found for registration.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="The academic year information for this course is missing. Please contact support.",
                )
            if (
                subject.faculty_id != logged_in_user.faculty_id
                or subject.department_id != logged_in_user.department_id
                or subject_year.year
                not in list(
                    range(logged_in_user_year.year, logged_in_user_year.year + 6)
                )
            ):
                await self.logger.log(
                    action="Register",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="User Tried to Register to a Subject Not Belonging to his Academic Data.",
                    details={"subject_id": subject_id},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="You can only register to courses belonging to your academic data",
                )

            existing_response = await self.user_subject_link_repository.find_one(
                and_(
                    UserSubjectLink.user_id == logged_in_user.id,
                    UserSubjectLink.subject_id == subject_id,
                )
            )
            if not existing_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_response.code,
                    data=None,
                    message=existing_response.message,
                )
            existing_link = existing_response.data
            if existing_link:
                await self.logger.log(
                    action="Register",
                    entity="Subject",
                    level="warning",
                    code=400,
                    message="User Tried to Register to a Subject He is Already Registered In.",
                    details={"user_id": logged_in_user.id, "subject_id": subject_id},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="You are already registered for this course",
                )

            link = UserSubjectLink(user_id=logged_in_user.id, subject_id=subject_id)
            create_response = await self.user_subject_link_repository.create(link)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            refresh_token = logged_in_user.refresh_token
            if refresh_token:
                await caching_handler.delete(f"system:{refresh_token}")
            await self.logger.log(
                action="Register",
                entity="Subject",
                level="info",
                code=200,
                message="User registered for subject successfully.",
                details={"user_id": logged_in_user.id, "subject_id": subject_id},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                message="Registered to course successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Register",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while registering for subject",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while registering for subject",
            )

    async def unregister(self, subject_id):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Unregister",
                    entity="Subject",
                    level="warning",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to retrieve logged in user for course unregistration. : {logged_in_user_response.message}",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Unregister",
                    entity="Subject",
                    level="warning",
                    code=401,
                    message="Unauthorized access attempt to unregister from course.",
                    details={},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False, code=401, data=None, message="Unauthorized"
                )
            existing_response = await self.user_subject_link_repository.find_one(
                and_(
                    UserSubjectLink.user_id == logged_in_user.id,
                    UserSubjectLink.subject_id == subject_id,
                ),
            )
            if not existing_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_response.code,
                    data=None,
                    message=existing_response.message,
                )
            existing_link = existing_response.data
            if not existing_link:
                await self.logger.log(
                    action="Unregister",
                    entity="Subject",
                    level="warning",
                    code=404,
                    message="User Tried to Unregister from a Course He is Not Registered In.",
                    details={"user_id": logged_in_user.id, "subject_id": subject_id},
                    source="SubjectService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="You are not registered for this course",
                )
            delete_response = await self.user_subject_link_repository.delete(
                existing_link
            )
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            refresh_token = logged_in_user.refresh_token
            if refresh_token:
                await caching_handler.delete(f"system:{refresh_token}")
            await self.logger.log(
                action="Unregister",
                entity="Subject",
                level="info",
                code=200,
                message="User unregistered from subject successfully.",
                details={"user_id": logged_in_user.id, "subject_id": subject_id},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=True, code=200, message="Unregistered successfully"
            )
        except Exception as ex:
            await self.logger.log(
                action="Unregister",
                entity="Subject",
                level="error",
                code=500,
                message="An error occurred while unregistering from subject",
                details={"error": repr(ex)},
                source="SubjectService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while unregistering from subject",
            )
