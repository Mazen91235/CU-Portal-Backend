import os
from typing import cast
from core.iServices.iAnnouncementService import IAnnouncementService
from core.iServices.iUserService import IUserService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.announcement import Announcement
from core.entities.subject import Subject
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.announcementDtos import (
    AnnouncementCreateDto,
    AnnouncementUpdateDto,
    AnnouncementResponseDto,
    AnnouncementSearchDto
)
from core.utils.timezoneHandler import TimezoneHandler


class AnnouncementService(IAnnouncementService):
    def __init__(
        self,
        announcement_repository: IBaseRepository[Announcement],
        subject_repository: IBaseRepository[Subject],
        user_service: IUserService,
        logger: IBaseLogger,
        helper_service: IHelperService,
        notification_service=None,  
    ):
        self.announcement_repository = announcement_repository
        self.subject_repository = subject_repository
        self.user_service = user_service
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
            return BaseResponseDto(success=True, data=announcement)
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

    # Business Logic Functions
    async def create(self, data: AnnouncementCreateDto) -> BaseResponseDto[AnnouncementResponseDto]:
        try:
            current_user_response = await self.user_service.get_current_user()
            if not current_user_response.success or not current_user_response.data:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="error",
                    code=current_user_response.code or 500,
                    message="Failed to retrieve logged in user",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=current_user_response.code,
                    data=None,
                    message=current_user_response.message or "User not found, please log in again.",
                )
            current_user = current_user_response.data

            date_date = None
            if data.date:
                date_date = TimezoneHandler.from_iso_to_utc(data.date)
                if date_date and date_date <= TimezoneHandler.now("UTC"):
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Past Date Provided for Announcement Creation.",
                        details={"data": data.model_dump()},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(success=False, code=400, message="Date must be a future date.")

            files = []
            if data.urls:
                for url in data.urls:
                    file_id = self.helper_service.get_file_id_from_url(url)
                    if not file_id:
                        await self.logger.log(
                            action="Create",
                            entity="Announcement",
                            level="warning",
                            code=400,
                            message="Invalid File URL in URLs List Provided for Announcement Creation.",
                            details={"data": data.model_dump(), "invalid_url": url},
                            source="AnnouncementService",
                        )
                        return BaseResponseDto(success=False, code=400, message="Invalid File provided")
                    
                    file_response = await self.helper_service.fetch_from_drive(file_id)
                    if not file_response.success or not file_response.data:
                        await self.logger.log(
                            action="Create",
                            entity="Announcement",
                            level="warning",
                            code=400,
                            message="Invalid File URL in URLs List Provided for Announcement Creation.",
                            details={"data": data.model_dump(), "invalid_url": url},
                            source="AnnouncementService",
                        )
                        return BaseResponseDto(success=False, code=400, message="Invalid File provided")
                    files.append(file_response.data)

            subject_response = await self.subject_repository.find_one(Subject.id == data.subject_id)
            if not subject_response.success or not subject_response.data:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Subject Not Found for Announcement Creation.",
                    details={"subject_id": data.subject_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(success=False, code=404, message="Subject not found")
            subject = subject_response.data

            if subject.faculty_id != current_user.faculty_id or subject.department_id != current_user.department_id or subject.year_id != current_user.year_id:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Subject Not Found or Does Not Belong to User's Faculty, Department, or Year for Announcement Creation.",
                    details={
                        "subject_id": data.subject_id,
                        "faculty_id": current_user.faculty_id,
                        "department_id": current_user.department_id,
                        "year_id": current_user.year_id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(success=False, code=404, message="Subject not found in your criteria")

            announcement = Announcement(
                title=data.title,
                content=data.content,
                date=date_date,
                faculty_id=current_user.faculty_id,
                department_id=current_user.department_id,
                year_id=current_user.year_id,
                subject_id=subject.id,
                author_id=current_user.id,
                urls=data.urls if data.urls and len(data.urls) > 0 else [],
                links=[link.model_dump() for link in data.links] if data.links and len(data.links) > 0 else [],
                details={"files_data": files if files and len(files) > 0 else []}
            )
            
            create_response = await self.announcement_repository.create(announcement)
            if not create_response.success:
                return BaseResponseDto(success=False, code=create_response.code, message=create_response.message)
                
            created_announcement = create_response.data
            
            if self.notification_service:
                try:
                    request = await self.helper_service.get_current_request()
                    date_str = f' on {created_announcement.date.strftime("%b %d, %Y")}' if created_announcement.date else ""
                    frontend_base = os.environ.get('FRONTEND_URL', '')
                    
                    await self.notification_service.create_notification(
                        request=request,
                        type="announcement",
                        entity_id=created_announcement.id,
                        message=f'New announcement "{created_announcement.title}" has been posted for subject "{subject.name}"{date_str}.',
                        url=f"{frontend_base}/user/announcements/{created_announcement.id}"
                    )
                except Exception:
                    pass
            
            await self.logger.log(
                action="Create",
                entity="Announcement",
                level="info",
                code=201,
                message="Announcement Created Successfully.",
                details={"announcement_id": created_announcement.id},
                source="AnnouncementService",
            )
            
            return BaseResponseDto(
                success=True, 
                code=201, 
                message="Announcement created successfully", 
                data=AnnouncementResponseDto.model_validate(created_announcement)
            )
            
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Announcement",
                level="error",
                code=500,
                message="An Error Occurred while Creating Announcement.",
                details={"error": str(ex)},
                source="AnnouncementService",
            )
            return BaseResponseDto(success=False, code=500, message="An error occurred while creating announcement. Please try again later.")

    async def update(self, announcement_id: int, data: AnnouncementUpdateDto) -> BaseResponseDto[AnnouncementResponseDto]:
        try:
            current_user_response = await self.user_service.get_current_user()
            if not current_user_response.success:
                return BaseResponseDto(success=False, code=401, message="User not found, please log in again.")
            current_user = current_user_response.data

            permissions_response = await self.user_service.get_user_permissions()
            permissions = permissions_response.data if permissions_response.success else []

            announcement_response = await self.announcement_repository.find_one(Announcement.id == announcement_id, ["author", "subject"])
            if not announcement_response.success or not announcement_response.data:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Announcement Not Found for Update.",
                    details={"announcement_id": announcement_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(success=False, code=404, message="Announcement not found")
            announcement = announcement_response.data

            if announcement.author_id != current_user.id and "Manage All Announcements" not in permissions:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="Unauthorized Announcement Update Attempt by Non-Author User.",
                    details={"announcement_id": announcement_id, "author_id": announcement.author_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(success=False, code=403, message="You are not authorized to update this announcement")

            subject_response = await self.subject_repository.find_one(Subject.id == data.subject_id)
            if not subject_response.success or not subject_response.data:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Subject Not Found for Announcement Update.",
                    details={"subject_id": data.subject_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(success=False, code=404, message="Subject not found")
            subject = subject_response.data

            if subject.faculty_id != current_user.faculty_id or subject.department_id != current_user.department_id or subject.year_id != current_user.year_id:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Subject Not Found or Does Not Belong to User's Faculty, Department, or Year for Announcement Update.",
                    details={
                        "subject_id": data.subject_id,
                        "faculty_id": current_user.faculty_id,
                        "department_id": current_user.department_id,
                        "year_id": current_user.year_id,
                    },
                    source="AnnouncementService",
                )
                return BaseResponseDto(success=False, code=404, message="Subject not found in your criteria")

            old_urls = [u for u in announcement.urls if u not in data.urls]
            for old_url in old_urls:
                file_id = self.helper_service.get_file_id_from_url(old_url)
                if file_id:
                    access_token_response = await self.helper_service.get_google_access_token(
                        current_user.google_refresh_token or ""
                    )
                    if access_token_response.success and access_token_response.data:
                        remove_response = await self.helper_service.delete_file_from_drive(access_token_response.data, file_id)
                        if not remove_response.success:
                            await self.logger.log(
                                action="Update",
                                entity="Announcement",
                                level="warning",
                                code=400,
                                message="Failed to Remove Old File from Drive during Announcement Update.",
                                details={"old_url": old_url},
                                source="AnnouncementService",
                            )
                            return BaseResponseDto(success=False, code=400, message="Failed to update announcement. Please try again later.")

            files = []
            if data.urls:
                for url in data.urls:
                    file_id = self.helper_service.get_file_id_from_url(url)
                    if not file_id:
                        return BaseResponseDto(success=False, code=400, message="Invalid File provided")
                    
                    file_response = await self.helper_service.fetch_from_drive(file_id)
                    if not file_response.success or not file_response.data:
                        return BaseResponseDto(success=False, code=400, message="Invalid File provided")
                    files.append(file_response.data)

            date_date = TimezoneHandler.from_iso_to_utc(data.date) if data.date else None
            
            announcement.title = data.title
            announcement.content = data.content
            announcement.date = date_date
            announcement.urls = data.urls if data.urls and len(data.urls) > 0 else []
            announcement.links = [link.model_dump() for link in data.links] if data.links and len(data.links) > 0 else []
            announcement.subject_id = subject.id
            announcement.author_id = current_user.id
            
            if files and len(files) > 0:
                announcement.details["files_data"] = files
            
            update_response = await self.announcement_repository.update(
                announcement, ["title", "content", "date", "urls", "links", "subject_id", "author_id", "details"]
            )
            if not update_response.success:
                return BaseResponseDto(success=False, code=update_response.code, message=update_response.message)

            if self.notification_service:
                try:
                    request = await self.helper_service.get_current_request()
                    date_str = f' on {announcement.date.strftime("%b %d, %Y")}' if announcement.date else ""
                    frontend_base = os.environ.get('FRONTEND_URL', '')
                    
                    await self.notification_service.create_notification(
                        request=request,
                        type="announcement",
                        entity_id=announcement.id,
                        message=f'Announcement "{announcement.title}" has been updated for subject "{subject.name}"{date_str}.',
                        url=f"{frontend_base}/user/announcements/{announcement.id}"
                    )
                except Exception:
                    pass
                
            await self.logger.log(
                action="Update",
                entity="Announcement",
                level="info",
                code=200,
                message="Announcement Updated Successfully.",
                details={"announcement_id": announcement.id},
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=True, 
                code=200, 
                message="Announcement updated successfully", 
                data=AnnouncementResponseDto.model_validate(update_response.data)
            )

        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Announcement",
                level="error",
                code=500,
                message="An Error Occurred while Updating Announcement.",
                details={"error": str(ex)},
                source="AnnouncementService",
            )
            return BaseResponseDto(success=False, code=500, message="An error occurred while updating announcement. Please try again later.")

    async def delete(self, announcement_id: int) -> BaseResponseDto[bool]:
        try:
            current_user_response = await self.user_service.get_current_user()
            if not current_user_response.success:
                return BaseResponseDto(success=False, code=401, message="User not found")
            current_user = current_user_response.data

            permissions_response = await self.user_service.get_user_permissions()
            permissions = permissions_response.data if permissions_response.success else []

            announcement_response = await self.announcement_repository.find_one(Announcement.id == announcement_id)
            if not announcement_response.success or not announcement_response.data:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Announcement Not Found for Deletion.",
                    details={"announcement_id": announcement_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(success=False, code=404, message="Announcement not found")
            announcement = announcement_response.data

            if announcement.author_id != current_user.id and "Manage All Announcements" not in permissions:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message="Unauthorized Announcement Deletion Attempt by Non-Author User.",
                    details={"announcement_id": announcement_id, "author_id": announcement.author_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(success=False, code=403, message="You are not authorized to delete this announcement")

            for url in announcement.urls or []:
                file_id = self.helper_service.get_file_id_from_url(url)
                if file_id:
                    access_token_response = await self.helper_service.get_google_access_token(current_user.google_refresh_token or "")
                    if access_token_response.success and access_token_response.data:
                        remove_response = await self.helper_service.delete_file_from_drive(access_token_response.data, file_id)
                        if not remove_response.success:
                            await self.logger.log(
                                action="Delete",
                                entity="Announcement",
                                level="warning",
                                code=400,
                                message="Failed to Remove File from Drive during Announcement Deletion.",
                                details={"url": url},
                                source="AnnouncementService",
                            )
                            return BaseResponseDto(success=False, code=400, message="Failed to delete announcement. Please try again later.")

            delete_response = await self.announcement_repository.delete(announcement)
            if not delete_response.success:
                return BaseResponseDto(success=False, code=delete_response.code, message=delete_response.message)

            await self.logger.log(
                action="Delete",
                entity="Announcement",
                level="info",
                code=200,
                message="Announcement Deleted Successfully.",
                details={"announcement_id": announcement_id},
                source="AnnouncementService",
            )
            return BaseResponseDto(success=True, code=200, message="Announcement deleted successfully", data=True)

        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Announcement",
                level="error",
                code=500,
                message="An Error Occurred while Deleting Announcement.",
                details={"error": str(ex)},
                source="AnnouncementService",
            )
            return BaseResponseDto(success=False, code=500, message="An error occurred while deleting announcement. Please try again later.")