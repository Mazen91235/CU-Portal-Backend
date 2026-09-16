import asyncio
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from core.iServices.iAttachmentService import IAttachmentService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.attachment import Attachment
from core.entities.announcement import Announcement
from core.entities.material import Material
from core.entities.pendingUser import PendingUser
from core.entities.task import Task
from core.entities.user import User
from core.dtos.baseDtos import BaseResponseDto
from core.utils.validator import Validator


class AttachmentService(IAttachmentService):
    def __init__(
        self,
        attachment_repository: IBaseRepository[Attachment],
        announcement_repository: IBaseRepository[Announcement],
        material_repository: IBaseRepository[Material],
        pending_user_repository: IBaseRepository[PendingUser],
        task_repository: IBaseRepository[Task],
        user_repository: IBaseRepository[User],
        logger: IBaseLogger,
        helper_service: IHelperService,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self.attachment_repository = attachment_repository
        self.announcement_repository = announcement_repository
        self.material_repository = material_repository
        self.pending_user_repository = pending_user_repository
        self.task_repository = task_repository
        self.user_repository = user_repository
        self.logger = logger
        self.helper_service = helper_service
        self.session_factory = session_factory
        self._background_tasks: set[asyncio.Task] = set()

    # Transaction Functions
    async def begin_transaction(self):
        await self.attachment_repository.begin_transaction()

    async def commit_transaction(self):
        await self.attachment_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.attachment_repository.rollback_transaction()

    # Attachment Specific Functions
    async def seed(self):
        try:
            announcements_response = await self.announcement_repository.find(
                limit=int(1e6)
            )
            if not announcements_response.success:
                return BaseResponseDto(
                    success=False,
                    code=announcements_response.code,
                    data=None,
                    message=announcements_response.message,
                )
            announcements = announcements_response.data or []
            for announcement in announcements:
                for url in announcement.urls:
                    await self.helper_service.create_attachment(
                        is_file=True,
                        url=url,
                        author_id=announcement.author_id,
                        source_name="announcement_id",
                        source_id=announcement.id,
                    )
                for link in announcement.links:
                    link_name = link.get("name", link.get("title", ""))
                    link_url = link.get("url", "")
                    await self.helper_service.create_attachment(
                        is_file=False,
                        url=link_url,
                        author_id=announcement.author_id,
                        source_name="announcement_id",
                        source_id=announcement.id,
                        link_title=link_name,
                    )
            materials_response = await self.material_repository.find(
                Material.material_type != "folder", limit=int(1e6)
            )
            if not materials_response.success:
                return BaseResponseDto(
                    success=False,
                    code=materials_response.code,
                    data=None,
                    message=materials_response.message,
                )
            materials = materials_response.data or []
            for material in materials:
                if material.material_type == "file":
                    await self.helper_service.create_attachment(
                        is_file=True,
                        url=material.url or "",
                        author_id=material.author_id,
                        source_name="material_id",
                        source_id=material.id,
                        fetched=(
                            material.details.get("fetched")
                            if material.details
                            else None
                        ),
                    )
                else:
                    await self.helper_service.create_attachment(
                        is_file=False,
                        url=material.url or "",
                        author_id=material.author_id,
                        source_name="material_id",
                        source_id=material.id,
                        link_title=material.name or "",
                    )
            pending_users_response = await self.pending_user_repository.find(
                limit=int(1e6)
            )
            if not pending_users_response.success:
                return BaseResponseDto(
                    success=False,
                    code=pending_users_response.code,
                    data=None,
                    message=pending_users_response.message,
                )
            pending_users = pending_users_response.data or []
            for pending_user in pending_users:
                await self.helper_service.create_attachment(
                    is_file=True,
                    url=pending_user.url or "",
                    author_id=pending_user.user_id,
                    source_name="pending_user_id",
                    source_id=pending_user.id,
                )
            tasks_response = await self.task_repository.find(limit=int(1e6))
            if not tasks_response.success:
                return BaseResponseDto(
                    success=False,
                    code=tasks_response.code,
                    data=None,
                    message=tasks_response.message,
                )
            tasks = tasks_response.data or []
            for task in tasks:
                for url in task.urls:
                    await self.helper_service.create_attachment(
                        is_file=True,
                        url=url,
                        author_id=task.author_id,
                        source_name="task_id",
                        source_id=task.id,
                    )
                for link in task.links:
                    link_name = link.get("name", link.get("title", ""))
                    link_url = link.get("url", "")
                    await self.helper_service.create_attachment(
                        is_file=False,
                        url=link_url,
                        author_id=task.author_id,
                        source_name="task_id",
                        source_id=task.id,
                        link_title=link_name,
                    )
            users_response = await self.user_repository.find(limit=int(1e6))
            if not users_response.success:
                return BaseResponseDto(
                    success=False,
                    code=users_response.code,
                    data=None,
                    message=users_response.message,
                )
            users = users_response.data or []
            for user in users:
                url = user.details.get("avatar", "")
                if not url or "lh3" in url or "googleusercontent" in url:
                    continue
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=user.id,
                    source_name="user_id",
                    source_id=user.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Seed",
                        entity="Attachment",
                        level="error",
                        code=attachment_response.code or 500,
                        message=attachment_response.message
                        or "An error occurred while creating attachment for user avatar, please try again.",
                        details={"error": attachment_response.error},
                        source="AttachmentService",
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
                        action="Seed",
                        entity="Attachment",
                        level="error",
                        code=500,
                        message="Attachment creation response did not contain an attachment object.",
                        source="AttachmentService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="Attachment creation response did not contain an attachment object.",
                    )
                user.avatar_id = attachment.id
                update_user_response = await self.user_repository.update(
                    user, ["avatar_id"]
                )
                if not update_user_response.success:
                    await self.logger.log(
                        action="Seed",
                        entity="Attachment",
                        level="error",
                        code=update_user_response.code or 500,
                        message=update_user_response.message
                        or "An error occurred while updating user with avatar attachment, please try again.",
                        source="AttachmentService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=update_user_response.code,
                        data=None,
                        message=update_user_response.message,
                    )
                updated_user = update_user_response.data
                if not updated_user:
                    await self.logger.log(
                        action="Seed",
                        entity="Attachment",
                        level="error",
                        code=500,
                        message="User update response did not contain an updated user object.",
                        source="AttachmentService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="User update response did not contain an updated user object.",
                    )
            await self.logger.log(
                action="Seed",
                entity="Attachment",
                level="info",
                code=200,
                message="Successfully updated user with avatar attachment",
                details={},
                source="AttachmentService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Successfully seeded attachments for announcements, materials, pending users, tasks, and users",
            )
        except Exception as ex:
            await self.logger.log(
                action="Seed",
                entity="Attachment",
                level="error",
                code=500,
                message="An error occurred while seeding attachments, please try again later",
                details={"error": repr(ex)},
                source="AttachmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while seeding attachments, please try again later",
            )

    async def validate(self):
        try:
            task = asyncio.create_task(self._validate())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Successfully validated attachments",
            )
        except Exception as ex:
            await self.logger.log(
                action="Validate",
                entity="Attachment",
                level="error",
                code=500,
                message="An error occurred while validating attachments, please try again later",
                details={"error": repr(ex)},
                source="AttachmentService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while validating attachments, please try again later",
            )
            
    # Helper Functions
    async def _validate(self):
        async with self.session_factory() as session:
            try:
                await session.begin()
                dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Attachment, ["material", "pending_user.user"]
                )
                attachments_response = await self.attachment_repository.find(
                    Attachment.is_file == True, dynamic_includes, limit=int(1e6), session=session
                )
                if not attachments_response.success:
                    await session.rollback()
                    return BaseResponseDto(
                        success=False,
                        code=attachments_response.code,
                        data=None,
                        message=attachments_response.message,
                    )
                attachments = attachments_response.data or []
                deleted = 0
                for attachment in attachments:
                    file_exists_response = (
                        await self.helper_service.verify_file_exists_on_drive(
                            attachment.url
                        )
                    )
                    if not file_exists_response.success or not file_exists_response.data:
                        await self.logger.log(
                            action="BackgroundValidate",
                            entity="Attachment",
                            level=(
                                "error" if not file_exists_response.success else "warning"
                            ),
                            code=(
                                (file_exists_response.code or 500)
                                if not file_exists_response.success
                                else 404
                            ),
                            message=(
                                (
                                    file_exists_response.message
                                    or "An error occurred while verifying file existence on Google Drive, please try again."
                                )
                                if not file_exists_response.success
                                else f"File for attachment with ID {attachment.id} does not exist on Google Drive."
                            ),
                            details={"error": file_exists_response.error},
                            source="AttachmentService",
                        )
                        if attachment.material is not None:
                            await self.logger.log(
                                action="BackgroundValidate",
                                entity="Attachment",
                                level="warning",
                                code=404,
                                message=f"File for attachment with ID {attachment.id} does not exist on Google Drive. Deleting Material with ID {attachment.material.id} as well.",
                                source="AttachmentService",
                            )
                            await self.material_repository.delete(attachment.material, session=session)
                        elif (
                            attachment.pending_user is not None
                            and attachment.pending_user.user is not None
                        ):
                            await self.logger.log(
                                action="BackgroundValidate",
                                entity="Attachment",
                                level="warning",
                                code=404,
                                message=f"File for attachment with ID {attachment.id} does not exist on Google Drive. Deleting User with ID {attachment.pending_user.user.id} and PendingUser with ID {attachment.pending_user.id} as well.",
                                source="AttachmentService",
                            )
                            await self.user_repository.delete(attachment.pending_user.user, session=session)
                        await self.helper_service.delete_attachment(attachment=attachment, session=session)
                        deleted += 1
                await session.commit()
                await self.logger.log(
                    action="BackgroundValidate",
                    entity="Attachment",
                    level="info",
                    code=200,
                    message=f"Successfully validated attachments. Deleted {deleted} attachments that did not have corresponding files on Google Drive.",
                    details={},
                    source="AttachmentService",
                )
                return BaseResponseDto(
                    success=True,
                    code=200,
                    data=None,
                    message="Successfully validated attachments",
                )
            except Exception as ex:
                await session.rollback()
                await self.logger.log(
                    action="BackgroundValidate",
                    entity="Attachment",
                    level="error",
                    code=500,
                    message="An error occurred while validating attachments, please try again later",
                    details={"error": repr(ex)},
                    source="AttachmentService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while validating attachments, please try again later",
                )
            finally:
                await session.close()
