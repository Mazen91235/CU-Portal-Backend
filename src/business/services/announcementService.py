from sqlalchemy import and_
from core.iServices.iAnnouncementService import IAnnouncementService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.announcement import Announcement
from core.entities.subject import Subject
from core.entities.notification import Notification
from core.dtos.baseDtos import BaseResponseDto
from core.utils.validator import Validator


class AnnouncementService(IAnnouncementService):
    def __init__(
        self,
        announcement_repository: IBaseRepository[Announcement],
        subject_repository: IBaseRepository[Subject],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.announcement_repository = announcement_repository
        self.subject_repository = subject_repository
        self.logger = logger
        self.helper_service = helper_service

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
                "Announcement", order_by, descending
            )
            result = await self.announcement_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by
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
                details={"error": repr(ex)},
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
                "Announcement", order_by, descending
            )
            result = await self.announcement_repository.find(
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

            announcements = result.data
            return BaseResponseDto(
                success=True, data=announcements, next_page=result.next_page
            )

        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while finding announcements",
                details={"error": repr(ex)},
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
                        Announcement.date.is_not_distinct_from(data.date),
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
            subject_response = await self.subject_repository.find_one(
                Subject.id == data.subject_id
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
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id,
                    department_id=data.department_id,
                    year_id=data.year_id,
                    subject_id=data.subject_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user {logged_in_user.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to create announcement for the specified criteria.",
                )
            data.faculty_id = data.faculty_id or logged_in_user.faculty_id
            data.department_id = data.department_id or logged_in_user.department_id
            data.year_id = data.year_id or logged_in_user.year_id
            data.details = {} if not data.details else data.details
            urls = data.details.get("urls", [])
            links = data.details.get("links", [])
            data.details.pop("urls", None)
            data.details.pop("links", None)
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
            for url in urls:
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=logged_in_user.id,
                    source_name="announcement_id",
                    source_id=created_announcement.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Failed to create attachment for announcement.",
                        details={"url": url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Failed to create attachment for announcement without a specific error.",
                        details={"url": url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="An error occurred while creating attachment for announcement",
                    )
            for link in links:
                link_name = link.get("name") or link.get("title") or "Untitled Link"
                link_url = link.get("url", "")
                attachment_response = await self.helper_service.create_attachment(
                    is_file=False,
                    url=link_url,
                    author_id=logged_in_user.id,
                    source_name="announcement_id",
                    source_id=created_announcement.id,
                    link_title=link_name,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for announcement.",
                        details={"url": link_url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Create",
                        entity="Announcement",
                        level="warning",
                        code=400,
                        message="Failed to create attachment for announcement without a specific error.",
                        details={"url": link_url},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="An error occurred while creating attachment for announcement",
                    )
            share_link = f"/user/announcements/{created_announcement.id}"
            await self.helper_service.send_notification(
                Notification.NotificationType.ANNOUNCEMENT,
                created_announcement.id,
                f"New announcement '{created_announcement.title}' has been created for subject {subject.name}.",
                share_link,
                subject_id=created_announcement.subject_id,
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
            print(ex)
            await self.logger.log(
                action="Create",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while creating announcement",
                details={"error": repr(ex)},
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
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Announcement, ["attachments"]
            )
            target_announcement_response = await self.announcement_repository.find_one(
                Announcement.id == data.id, dynamic_includes
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
            subject_response = await self.subject_repository.find_one(
                Subject.id == data.subject_id
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
                    message="Subject not found for Announcement Update.",
                    details={"subject_id": data.subject_id},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Subject not found",
                )
            existing_announcement_response = (
                await self.announcement_repository.find_one(
                    and_(
                        Announcement.title == data.title,
                        Announcement.subject_id == data.subject_id,
                        Announcement.date.is_not_distinct_from(data.date),
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
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id,
                    department_id=data.department_id,
                    year_id=data.year_id,
                    subject_id=data.subject_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user {logged_in_user.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to update announcement for the specified criteria.",
                )
            data.faculty_id = data.faculty_id or logged_in_user.faculty_id
            data.department_id = data.department_id or logged_in_user.department_id
            data.year_id = data.year_id or logged_in_user.year_id
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Announcement Update.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating announcement",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Announcement Update.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating announcement",
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
            old_attachments = target_announcement.attachments or set()
            data.details = {} if not data.details else data.details
            urls = data.details.get("urls", [])
            links = data.details.get("links", [])
            data.details.pop("urls", None)
            data.details.pop("links", None)
            target_announcement.title = data.title
            target_announcement.content = data.content
            target_announcement.date = data.date
            target_announcement.subject_id = data.subject_id
            target_announcement.faculty_id = data.faculty_id
            target_announcement.department_id = data.department_id
            target_announcement.year_id = data.year_id
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
            new_urls = [
                u
                for u in urls
                if u not in [a.url for a in old_attachments if a.is_file]
            ]
            to_be_removed_attachments = []
            for attachment in old_attachments:
                if attachment.is_file and attachment.url not in urls:
                    to_be_removed_attachments.append(attachment)
                elif not attachment.is_file and not any(
                    link.get("url", "") == attachment.url for link in links
                ):
                    to_be_removed_attachments.append(attachment)
            for attachment in to_be_removed_attachments:
                await self.helper_service.delete_attachment(attachment=attachment)
            for url in new_urls:
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=logged_in_user.id,
                    source_name="announcement_id",
                    source_id=updated_announcement.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Attachment",
                        level="error",
                        code=attachment_response.code or 500,
                        message=f"Failed to create attachment for URL {url}: {attachment_response.message}",
                        details={"error": attachment_response.error},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Create",
                        entity="Attachment",
                        level="error",
                        code=500,
                        message=f"Failed to create attachment for URL {url} without a specific error.",
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating attachment for announcement",
                    )
            for link in links:
                link_name = link.get("name") or link.get("title") or "Untitled Link"
                link_url = link.get("url", "")
                attachment = next(
                    (a for a in old_attachments if a.url == link_url and not a.is_file),
                    None,
                )
                if attachment:
                    attachment.details["link_title"] = link_name
                    attachment_response = await self.helper_service.update_attachment(
                        attachment=attachment
                    )
                    if not attachment_response.success:
                        await self.logger.log(
                            action="Update",
                            entity="Attachment",
                            level="error",
                            code=attachment_response.code or 500,
                            message=f"Failed to update attachment for link {link_url}: {attachment_response.message}",
                            details={"error": attachment_response.error},
                            source="AnnouncementService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=attachment_response.code,
                            data=None,
                            message=attachment_response.message,
                        )
                    continue
                attachment_response = await self.helper_service.create_attachment(
                    is_file=False,
                    url=link_url,
                    author_id=logged_in_user.id,
                    source_name="announcement_id",
                    source_id=updated_announcement.id,
                    link_title=link_name,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Attachment",
                        level="error",
                        code=attachment_response.code or 500,
                        message=f"Failed to create attachment for link {link_url}: {attachment_response.message}",
                        details={"error": attachment_response.error},
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Create",
                        entity="Attachment",
                        level="error",
                        code=500,
                        message=f"Failed to create attachment for link {link_url} without a specific error.",
                        source="AnnouncementService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating attachment for announcement",
                    )
            share_link = f"/user/announcements/{updated_announcement.id}"
            await self.helper_service.send_notification(
                Notification.NotificationType.ANNOUNCEMENT,
                updated_announcement.id,
                f"Announcement '{updated_announcement.title}' has been updated for subject {subject.name}.",
                share_link,
                subject_id=updated_announcement.subject_id,
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
                details={"error": repr(ex)},
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
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Announcement, ["attachments"]
            )
            target_announcement_response = await self.announcement_repository.find_one(
                Announcement.id == data.id, dynamic_includes
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
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id,
                    department_id=data.department_id,
                    year_id=data.year_id,
                    subject_id=data.subject_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user {logged_in_user.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to delete announcement for the specified criteria.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Announcement Delete.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting announcement",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Delete",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Announcement Delete.",
                    source="AnnouncementService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting announcement",
                )
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
            to_be_removed_attachments = target_announcement.attachments or set()
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
            for attachment in to_be_removed_attachments:
                await self.helper_service.delete_attachment(attachment=attachment)
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
            print(ex)
            await self.logger.log(
                action="Delete",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while deleting announcement",
                details={"error": repr(ex)},
                source="AnnouncementService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting announcement",
            )
