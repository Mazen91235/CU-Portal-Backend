import os
from sqlalchemy import and_
from core.iServices.iAnnouncementService import IAnnouncementService
from core.iServices.iUserService import IUserService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.announcement import Announcement
from core.entities.subject import Subject
from core.entities.role import Role
from core.entities.faculty import Faculty
from core.entities.department import Department
from core.entities.year import Year
from core.dtos.baseDtos import BaseResponseDto
from core.utils.validator import Validator


class AnnouncementService(IAnnouncementService):
    def __init__(
        self,
        announcement_repository: IBaseRepository[Announcement],
        subject_repository: IBaseRepository[Subject],
        role_repository: IBaseRepository[Role],
        faculty_repository: IBaseRepository[Faculty],
        department_repository: IBaseRepository[Department],
        year_repository: IBaseRepository[Year],
        logger: IBaseLogger,
        helper_service: IHelperService,
        notification_service=None,
    ):
        self.announcement_repository = announcement_repository
        self.subject_repository = subject_repository
        self.role_repository = role_repository
        self.faculty_repository = faculty_repository
        self.department_repository = department_repository
        self.year_repository = year_repository
        self.logger = logger
        self.helper_service = helper_service
        self.notification_service = notification_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.announcement_repository.begin_transaction()

    async def commit_transaction(self):
        await self.announcement_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.announcement_repository.rollback_transaction()

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
                Announcement, data, ["title", "content"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Announcement, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Announcement", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Announcement", order_by
            )
            result = await self.announcement_repository.find_one(
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

            announcement = result.data
            return BaseResponseDto(
                success=True,
                data=announcement,
            )
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while finding announcement",
                details={"error": str(ex)},
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding announcement",
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
                Announcement, data, ["title", "content"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Announcement, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Announcement", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Announcement", order_by
            )

            result = await self.announcement_repository.find(
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

            announcements = result.data
            return BaseResponseDto(success=True, data=announcements)

        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while finding announcements",
                details={"error": str(ex)},
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding announcements",
            )

    async def create(self, data):
        try:
            existing_announcement_response = (
                await self.announcement_repository.find_one(
                    and_(
                        Announcement.title == data.title,
                        Announcement.subject_id == data.subject_id,
                    )
                )
            )
            if not existing_announcement_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_announcement_response.code,
                    data=None,
                    message=existing_announcement_response.message,
                )
            existing_announcement = existing_announcement_response.data
            if existing_announcement:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="warning",
                    code=400,
                    message="Announcement with the same title already exists for this subject.",
                    details={"title": data.title, "subject_id": data.subject_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Announcement with the same title already exists for this subject.",
                )
            files = []
            for url in data.urls:
                file_exists_response = (
                    await self.helper_service.verify_file_exists_on_drive(url)
                )
                if not file_exists_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="File does not exist on Google Drive for Announcement Creation.",
                        details={"url": url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=file_exists_response.code,
                        data=None,
                        message=file_exists_response.message,
                    )
                file_data = file_exists_response.data
                if not file_data:
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Failed to fetch file data from Google Drive for Announcement Creation.",
                        details={"url": url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Failed to fetch file data from Google Drive",
                    )
                files.append(file_data.model_dump())
            for link_name, link_url in (data.links).items():
                if not Validator.is_valid_external_url(link_url):
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Invalid URL provided for Announcement Creation.",
                        details={"link_name": link_name, "link_url": link_url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid URL provided",
                    )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Announcement Creation.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating announcement",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="No logged-in user found for Announcement Creation.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating announcement",
                )
            data.author_id = logged_in_user.id
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Role, ["exact_roles"]
            )
            logged_in_user_role_response = await self.role_repository.find_one(
                Role.id == logged_in_user.role_id, dynamic_includes
            )
            if not logged_in_user_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_role_response.code,
                    data=None,
                    message=logged_in_user_role_response.message,
                )
            logged_in_user_role = logged_in_user_role_response.data
            if not logged_in_user_role:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Logged-in user's role not found for Announcement Creation.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating announcement",
                )
            logged_in_user_permissions = [
                perm.name for perm in logged_in_user_role.exact_roles
            ]
            if "Access All Faculties" not in logged_in_user_permissions:
                data.faculty_id = logged_in_user.faculty_id
            else:
                if not data.faculty_id:
                    data.faculty_id = logged_in_user.faculty_id
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
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=404,
                        message="Faculty not found for Announcement Creation.",
                        details={"faculty_id": data.faculty_id},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Faculty not found",
                    )
            if "Access All Departments" not in logged_in_user_permissions:
                data.department_id = logged_in_user.department_id
            else:
                if not data.department_id:
                    data.department_id = logged_in_user.department_id
                department_response = await self.department_repository.find_one(
                    Department.id == data.department_id
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
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=404,
                        message="Department not found for Announcement Creation.",
                        details={"department_id": data.department_id},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Department not found",
                    )
                if department.faculty_id != data.faculty_id:
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Department does not belong to the specified faculty for Announcement Creation.",
                        details={
                            "department_id": data.department_id,
                            "faculty_id": data.faculty_id,
                        },
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Department does not belong to the specified faculty",
                    )
                if (
                    department.faculty_id != logged_in_user.faculty_id
                    and "Access All Faculties" not in logged_in_user_permissions
                ):
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=403,
                        message="User does not have permission to create announcement for this department.",
                        details={
                            "user_id": logged_in_user.id,
                            "department_id": data.department_id,
                        },
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=403,
                        data=None,
                        message="You do not have permission to create an announcement for this department.",
                    )
            if "Access All Years" not in logged_in_user_permissions:
                data.year_id = logged_in_user.year_id
            else:
                if not data.year_id:
                    data.year_id = logged_in_user.year_id
                year_response = await self.year_repository.find_one(
                    Year.id == data.year_id
                )
                if not year_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=year_response.code,
                        data=None,
                        message=year_response.message,
                    )
                year = year_response.data
                if not year:
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=404,
                        message="Year not found for Announcement Creation.",
                        details={"year_id": data.year_id},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Year not found",
                    )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Subject, ["users"]
            )
            subject_response = await self.subject_repository.find_one(
                Subject.id == data.subject_id, dynamic_includes
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
                    action="Create",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Subject not found for Announcement Creation.",
                    details={"subject_id": data.subject_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Subject not found",
                )
            user_ids = [user.id for user in subject.users] if subject.users else []
            if (
                logged_in_user.id not in user_ids
                and "Access All Courses" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to create announcement for this subject.",
                    details={
                        "user_id": logged_in_user.id,
                        "subject_id": data.subject_id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to create an announcement for this subject.",
                )

            data.details = {"files_data": files} if files else {}

            create_announcement_response = await self.announcement_repository.create(
                data
            )
            if not create_announcement_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_announcement_response.code,
                    data=None,
                    message=create_announcement_response.message,
                )
            created_announcement = create_announcement_response.data
            if not created_announcement:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to create announcement without a specific error.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating announcement",
                )
            await self.logger.log(
                action="Create",
                entity="Announcement",
                level="info",
                code=201,
                message="Announcement created successfully",
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_announcement,
                message="Announcement created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while creating announcement",
                details={"error": str(ex)},
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating announcement",
            )

    async def update(self, data):
        try:
            target_announcement_response = await self.announcement_repository.find_one(
                Announcement.id == data.id
            )
            if not target_announcement_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_announcement_response.code,
                    data=None,
                    message=target_announcement_response.message,
                )
            target_announcement = target_announcement_response.data
            if not target_announcement:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="info",
                    code=404,
                    message="Announcement not found for update",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Announcement not found",
                )
            existing_announcement_response = (
                await self.announcement_repository.find_one(
                    and_(
                        Announcement.title == data.title,
                        Announcement.subject_id == data.subject_id,
                    )
                )
            )
            if not existing_announcement_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_announcement_response.code,
                    data=None,
                    message=existing_announcement_response.message,
                )
            existing_announcement = existing_announcement_response.data
            if existing_announcement and existing_announcement.id != data.id:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=400,
                    message="Another announcement with the same title already exists for this subject.",
                    details={"title": data.title, "subject_id": data.subject_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Another announcement with the same title already exists for this subject.",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Announcement Update.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating announcement",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="No logged-in user found for Announcement Update.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating announcement",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Role, ["exact_roles"]
            )
            logged_in_user_role_response = await self.role_repository.find_one(
                Role.id == logged_in_user.role_id, dynamic_includes
            )
            if not logged_in_user_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_role_response.code,
                    data=None,
                    message=logged_in_user_role_response.message,
                )
            logged_in_user_role = logged_in_user_role_response.data
            if not logged_in_user_role:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Logged-in user's role not found for Announcement Update.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating announcement",
                )
            logged_in_user_permissions = [
                perm.name for perm in logged_in_user_role.exact_roles
            ]
            if (
                "Access All Faculties" not in logged_in_user_permissions
                and target_announcement.faculty_id != logged_in_user.faculty_id
            ):
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to update this announcement.",
                    details={
                        "user_id": logged_in_user.id,
                        "announcement_id": target_announcement.id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to update this announcement.",
                )
            if "Access All Faculties" not in logged_in_user_permissions:
                data.faculty_id = logged_in_user.faculty_id
            else:
                if not data.faculty_id:
                    data.faculty_id = target_announcement.faculty_id
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
                        entity="Announcement",
                        level="warning",
                        code=404,
                        message="Faculty not found for Announcement Update.",
                        details={"faculty_id": data.faculty_id},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Faculty not found",
                    )
            if (
                "Access All Departments" not in logged_in_user_permissions
                and target_announcement.department_id != logged_in_user.department_id
            ):
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to update this announcement.",
                    details={
                        "user_id": logged_in_user.id,
                        "announcement_id": target_announcement.id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to update this announcement.",
                )
            if "Access All Departments" not in logged_in_user_permissions:
                data.department_id = logged_in_user.department_id
            else:
                if not data.department_id:
                    data.department_id = target_announcement.department_id
                department_response = await self.department_repository.find_one(
                    Department.id == data.department_id
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
                        entity="Announcement",
                        level="warning",
                        code=404,
                        message="Department not found for Announcement Update.",
                        details={"department_id": data.department_id},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Department not found",
                    )
                if department.faculty_id != data.faculty_id:
                    await self.logger.log(
                        action="Update",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Department does not belong to the specified faculty for Announcement Update.",
                        details={
                            "department_id": data.department_id,
                            "faculty_id": data.faculty_id,
                        },
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Department does not belong to the specified faculty",
                    )
                if (
                    department.faculty_id != logged_in_user.faculty_id
                    and "Access All Faculties" not in logged_in_user_permissions
                ):
                    await self.logger.log(
                        action="Update",
                        entity="Announcement",
                        level="warning",
                        code=403,
                        message="User does not have permission to update announcement for this department.",
                        details={
                            "user_id": logged_in_user.id,
                            "department_id": data.department_id,
                        },
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=403,
                        data=None,
                        message="You do not have permission to update an announcement for this department.",
                    )
            if (
                "Access All Years" not in logged_in_user_permissions
                and target_announcement.year_id != logged_in_user.year_id
            ):
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to update this announcement.",
                    details={
                        "user_id": logged_in_user.id,
                        "announcement_id": target_announcement.id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to update this announcement.",
                )
            if "Access All Years" not in logged_in_user_permissions:
                data.year_id = logged_in_user.year_id
            else:
                if not data.year_id:
                    data.year_id = target_announcement.year_id
                year_response = await self.year_repository.find_one(
                    Year.id == data.year_id
                )
                if not year_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=year_response.code,
                        data=None,
                        message=year_response.message,
                    )
                year = year_response.data
                if not year:
                    await self.logger.log(
                        action="Update",
                        entity="Announcement",
                        level="warning",
                        code=404,
                        message="Year not found for Announcement Update.",
                        details={"year_id": data.year_id},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Year not found",
                    )
            if (
                logged_in_user.id != target_announcement.author_id
                and "Manage All Announcements" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to update this announcement.",
                    details={
                        "user_id": logged_in_user.id,
                        "announcement_id": target_announcement.id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to update this announcement.",
                )
            data.author_id = logged_in_user.id
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Subject, ["users"]
            )
            target_announcement_subject_response = (
                await self.subject_repository.find_one(
                    Subject.id == target_announcement.subject_id, dynamic_includes
                )
            )
            if not target_announcement_subject_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_announcement_subject_response.code,
                    data=None,
                    message=target_announcement_subject_response.message,
                )
            target_announcement_subject = target_announcement_subject_response.data
            if not target_announcement_subject:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Subject of the target announcement not found for update.",
                    details={"subject_id": target_announcement.subject_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Subject of the target announcement not found.",
                )
            target_announcement_subject_user_ids = (
                [user.id for user in target_announcement_subject.users]
                if target_announcement_subject.users
                else []
            )
            if (
                logged_in_user.id not in target_announcement_subject_user_ids
                and "Access All Courses" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to update announcement for this subject.",
                    details={
                        "user_id": logged_in_user.id,
                        "target_subject_id": target_announcement.subject_id,
                        "new_subject_id": data.subject_id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to update announcement for this subject.",
                )
            subject_response = await self.subject_repository.find_one(
                Subject.id == data.subject_id, dynamic_includes
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
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="New subject not found for announcement update.",
                    details={"new_subject_id": data.subject_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="New subject not found.",
                )
            subject_user_ids = (
                [user.id for user in subject.users] if subject.users else []
            )
            if (
                logged_in_user.id not in subject_user_ids
                and "Access All Courses" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to update announcement for the new subject.",
                    details={
                        "user_id": logged_in_user.id,
                        "new_subject_id": data.subject_id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to update announcement for the new subject.",
                )
            old_urls = target_announcement.urls or []
            to_be_removed_urls = (
                [url for url in old_urls if url not in data.urls]
                if data.urls
                else old_urls
            )
            files = []
            for url in data.urls:
                file_exists_response = (
                    await self.helper_service.verify_file_exists_on_drive(url)
                )
                if not file_exists_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="File does not exist on Google Drive for Announcement Update.",
                        details={"url": url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=file_exists_response.code,
                        data=None,
                        message=file_exists_response.message,
                    )
                file_data = file_exists_response.data
                if not file_data:
                    await self.logger.log(
                        action="Update",
                        entity="Announcement",
                        level="error",
                        code=500,
                        message="Failed to fetch file data from Google Drive for Announcement Update.",
                        details={"url": url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating announcement",
                    )
                files.append(file_data.model_dump())
            for link_name, link_url in (data.links).items():
                if not Validator.is_valid_external_url(link_url):
                    await self.logger.log(
                        action="Update",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Invalid URL provided for Announcement Update.",
                        details={"link_name": link_name, "link_url": link_url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid URL provided",
                    )
            data.details = {"files_data": files} if files else {}
            target_announcement.title = data.title
            target_announcement.content = data.content
            target_announcement.date = data.date
            target_announcement.subject_id = data.subject_id
            target_announcement.faculty_id = data.faculty_id
            target_announcement.department_id = data.department_id
            target_announcement.year_id = data.year_id
            target_announcement.urls = data.urls
            target_announcement.links = data.links
            target_announcement.details = data.details
            target_announcement.author_id = data.author_id
            update_response = await self.announcement_repository.update(
                target_announcement
            )
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_announcement = update_response.data
            if not updated_announcement:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to update announcement without a specific error.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating announcement",
                )
            if len(to_be_removed_urls) > 0:
                remove_response = await self.helper_service.remove_files_from_drive(
                    [
                        {
                            "user_id": updated_announcement.author_id,
                            "file_id": self.helper_service.get_file_id_from_url(url),
                        }
                        for url in to_be_removed_urls
                    ]
                )
                if not remove_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Failed to Remove Files from Drive during Announcement Update.",
                        details={"urls": to_be_removed_urls},
                        source="AnnouncementService",
                    )
            await self.logger.log(
                action="Update",
                entity="Announcement",
                level="info",
                code=200,
                message="Announcement updated successfully",
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_announcement,
                message="Announcement updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while updating announcement",
                details={"error": str(ex)},
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating announcement",
            )

    async def delete(self, data):
        try:
            target_announcement_response = await self.announcement_repository.find_one(
                Announcement.id == data.id
            )
            if not target_announcement_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_announcement_response.code,
                    data=None,
                    message=target_announcement_response.message,
                )
            target_announcement = target_announcement_response.data
            if not target_announcement:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Announcement not found for deletion",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Announcement not found",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Announcement Deletion.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting announcement",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="No logged-in user found for Announcement Deletion.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting announcement",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Role, ["exact_roles"]
            )
            logged_in_user_role_response = await self.role_repository.find_one(
                Role.id == logged_in_user.role_id, dynamic_includes
            )
            if not logged_in_user_role_response.success:
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_role_response.code,
                    data=None,
                    message=logged_in_user_role_response.message,
                )
            logged_in_user_role = logged_in_user_role_response.data
            if not logged_in_user_role:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Logged-in user's role not found for Announcement Deletion.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting announcement",
                )
            logged_in_user_permissions = [
                perm.name for perm in logged_in_user_role.exact_roles
            ]
            if (
                logged_in_user.id != target_announcement.author_id
                and "Manage All Announcements" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to delete this announcement.",
                    details={
                        "user_id": logged_in_user.id,
                        "announcement_id": target_announcement.id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to delete this announcement.",
                )
            if (
                "Access All Faculties" not in logged_in_user_permissions
                and target_announcement.faculty_id != logged_in_user.faculty_id
            ):
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to delete this announcement.",
                    details={
                        "user_id": logged_in_user.id,
                        "announcement_id": target_announcement.id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to delete this announcement.",
                )
            if (
                "Access All Departments" not in logged_in_user_permissions
                and target_announcement.department_id != logged_in_user.department_id
            ):
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to delete this announcement.",
                    details={
                        "user_id": logged_in_user.id,
                        "announcement_id": target_announcement.id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to delete this announcement.",
                )
            if (
                "Access All Years" not in logged_in_user_permissions
                and target_announcement.year_id != logged_in_user.year_id
            ):
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to delete this announcement.",
                    details={
                        "user_id": logged_in_user.id,
                        "announcement_id": target_announcement.id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to delete this announcement.",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Subject, ["users"]
            )
            target_announcement_subject_response = (
                await self.subject_repository.find_one(
                    Subject.id == target_announcement.subject_id, dynamic_includes
                )
            )
            if not target_announcement_subject_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_announcement_subject_response.code,
                    data=None,
                    message=target_announcement_subject_response.message,
                )
            target_announcement_subject = target_announcement_subject_response.data
            if not target_announcement_subject:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Subject of the target announcement not found for deletion.",
                    details={"subject_id": target_announcement.subject_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Subject of the target announcement not found.",
                )
            target_announcement_subject_user_ids = (
                [user.id for user in target_announcement_subject.users]
                if target_announcement_subject.users
                else []
            )
            if (
                logged_in_user.id not in target_announcement_subject_user_ids
                and "Access All Courses" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="User does not have permission to delete announcement for this subject.",
                    details={
                        "user_id": logged_in_user.id,
                        "target_subject_id": target_announcement.subject_id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to delete announcement for this subject.",
                )
            delete_response = await self.announcement_repository.delete(
                target_announcement
            )
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            await self.logger.log(
                action="Delete",
                entity="Announcement",
                level="info",
                code=200,
                message="Announcement deleted successfully",
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Announcement deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while deleting announcement",
                details={"error": str(ex)},
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting announcement",
            )
