import os
from typing import cast
from core.iServices.iAnnouncementService import IAnnouncementService
from core.iServices.iUserService import IUserService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.announcement import Announcement
from core.entities.subject import Subject
from core.entities.role import Role
from core.dtos.baseDtos import BaseResponseDto
from core.utils.timezoneHandler import TimezoneHandler


class AnnouncementService(IAnnouncementService):
    def __init__(
        self,
        announcement_repository: IBaseRepository[Announcement],
        subject_repository: IBaseRepository[Subject],
        logger: IBaseLogger,
        helper_service: IHelperService,
        notification_service=None,  
    ):
        self.announcement_repository = announcement_repository
        self.subject_repository = subject_repository
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

            if announcement:
                user_res = await self.helper_service.get_logged_in_user()
                if user_res and user_res.success and user_res.data:
                    current_user = user_res.data
                    role_res = await self.role_repository.find_one(
                        predicate=(Role.id == current_user.role_id), 
                        includes=["permissions"]
                    )
                    
                    permissions = []
                    if role_res.success and role_res.data:
                        permissions = [p.name for p in role_res.data.permissions]
                    if "View Announcements" not in permissions:
                        if (announcement.faculty_id != current_user.faculty_id or 
                            announcement.department_id != current_user.department_id or 
                            announcement.year_id != current_user.year_id):
                            
                            await self.logger.log(
                                action="FindOne",
                                entity="Announcement",
                                level="warning",
                                code=403,
                                message="Unauthorized access to announcement",
                                source="AnnouncementService",
                            )
                            return BaseResponseDto(
                                success=False,
                                code=403,
                                data=None,
                                message="You are not authorized to view this announcement"
                            )
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
            user_res = await self.helper_service.get_logged_in_user()
            if user_res and user_res.success and user_res.data:
                current_user = user_res.data
                role_res = await self.role_repository.find_one(
                    predicate=(Role.id == current_user.role_id),
                    includes=["permissions"] 
                )
                
                permissions = []
                if role_res.success and role_res.data:
                    permissions = [p.name for p in role_res.data.permissions] 
                if data:
                    if "View Announcements" not in permissions:
                        data.faculty_id = current_user.faculty_id
                        data.department_id = current_user.department_id
                        data.year_id = current_user.year_id
                    else:
                        if "Access All Faculties" not in permissions:
                            data.faculty_id = current_user.faculty_id
                        if "Access All Departments" not in permissions:
                            data.department_id = current_user.department_id
                        if "Access All Years" not in permissions:
                            data.year_id = current_user.year_id

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
    async def create(self, data):
        try:
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
                            details={"invalid_url": url},
                            source="AnnouncementService",
                        )
                        return BaseResponseDto(
                            success=False, 
                            code=400, 
                            data=None, 
                            message="Invalid File provided"
                        )
                    
                    file_response = await self.helper_service.fetch_from_drive(file_id)
                    if not file_response.success or not file_response.data:
                        await self.logger.log(
                            action="Create",
                            entity="Announcement",
                            level="warning",
                            code=400,
                            message="Invalid File URL in URLs List Provided for Announcement Creation.",
                            details={"invalid_url": url},
                            source="AnnouncementService",
                        )
                        return BaseResponseDto(
                            success=False, 
                            code=400, 
                            data=None, 
                            message="Invalid File provided"
                        )
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
                return BaseResponseDto(
                    success=False, 
                    code=404, 
                    data=None, 
                    message="Subject not found"
                )

            if not data.urls:
                data.urls = []
            if not data.links:
                data.links = []
                
            data.details = {"files_data": files} if files else {}

            create_res = await self.announcement_repository.create(data)
            if not create_res.success:
                return BaseResponseDto(
                    success=False, 
                    code=create_res.code, 
                    data=None, 
                    message=create_res.message
                )
                
            created_announcement = create_res.data
            
            if not created_announcement:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to create announcement without a specific error",
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
                message="An error occurred while creating announcement"
            )
        
    async def update(self, data):
        try:
            target_res = await self.announcement_repository.find_one(
                Announcement.id == data.id
            )
            if not target_res.success:
                return BaseResponseDto(
                    success=False,
                    code=target_res.code,
                    data=None,
                    message=target_res.message,
                )
                
            target_announcement = target_res.data
            if not target_announcement:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="info",
                    code=404,
                    message="Announcement not found",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Announcement not found",
                )

            subject_response = await self.subject_repository.find_one(Subject.id == data.subject_id)
            if not subject_response.success or not subject_response.data:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=404,
                    message="Subject not found",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False, 
                    code=404, 
                    data=None, 
                    message="Subject not found"
                )

            old_urls = [u for u in target_announcement.urls if u not in (data.urls or [])]
            for old_url in old_urls:
                file_id = self.helper_service.get_file_id_from_url(old_url)
                if file_id:
                    access_token_response = await self.helper_service.get_google_access_token("")
                    if access_token_response.success and access_token_response.data:
                        remove_response = await self.helper_service.delete_file_from_drive(
                            access_token_response.data, file_id
                        )
                        if not remove_response.success:
                            await self.logger.log(
                                action="Update",
                                entity="Announcement",
                                level="warning",
                                code=400,
                                message="Failed to Remove Old File from Drive",
                                details={"old_url": old_url},
                                source="AnnouncementService",
                            )
                            return BaseResponseDto(
                                success=False, 
                                code=400, 
                                data=None, 
                                message="Failed to update announcement. Please try again later."
                            )

            files = []
            if data.urls:
                for url in data.urls:
                    file_id = self.helper_service.get_file_id_from_url(url)
                    if not file_id:
                        return BaseResponseDto(
                            success=False, 
                            code=400, 
                            data=None, 
                            message="Invalid File provided"
                        )
                    
                    file_response = await self.helper_service.fetch_from_drive(file_id)
                    if not file_response.success or not file_response.data:
                        return BaseResponseDto(
                            success=False, 
                            code=400, 
                            data=None, 
                            message="Invalid File provided"
                        )
                    files.append(file_response.data)

            target_announcement.title = data.title
            target_announcement.content = data.content
            target_announcement.date = data.date
            target_announcement.urls = data.urls if data.urls else []
            target_announcement.links = data.links if data.links else []
            target_announcement.subject_id = data.subject_id
            
            if files:
                target_announcement.details = {"files_data": files}
            else:
                target_announcement.details = {}

            update_res = await self.announcement_repository.update(
                target_announcement, 
                ["title", "content", "date", "urls", "links", "subject_id", "details"]
            )
            
            if not update_res.success:
                return BaseResponseDto(
                    success=False,
                    code=update_res.code,
                    message=update_res.message,
                )
                
            updated_announcement = update_res.data
            if not updated_announcement:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to update announcement without a specific error",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating announcement",
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
                data=updated_announcement
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
            result = await self.announcement_repository.find_one(
                predicate=(Announcement.id == data.id)
            )
            
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
                
            announcement = result.data
            
            if not announcement:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="info",
                    code=404,
                    message="Announcement not found",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Announcement not found",
                )

            for url in announcement.urls or []:
                file_id = self.helper_service.get_file_id_from_url(url)
                if file_id:
                    access_token_response = await self.helper_service.get_google_access_token("")
                    if access_token_response.success and access_token_response.data:
                        remove_response = await self.helper_service.delete_file_from_drive(
                            access_token_response.data, file_id
                        )
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
                            return BaseResponseDto(
                                success=False, 
                                code=400, 
                                data=None, 
                                message="Failed to delete announcement files. Please try again later."
                            )

            delete_res = await self.announcement_repository.delete(announcement)
            
            if not delete_res.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_res.code,
                    data=None,
                    message=delete_res.message,
                )

            await self.logger.log(
                action="Delete",
                entity="Announcement",
                level="info",
                code=200,
                message="Announcement deleted successfully",
                source="AnnouncementService",
            )
            return BaseResponseDto(success=True, code=200, data=True)

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