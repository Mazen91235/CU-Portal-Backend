import asyncio
from sqlalchemy import and_
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
    ):
        self.attachment_repository = attachment_repository
        self.announcement_repository = announcement_repository
        self.material_repository = material_repository
        self.pending_user_repository = pending_user_repository
        self.task_repository = task_repository
        self.user_repository = user_repository
        self.logger = logger
        self.helper_service = helper_service

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
                if not url:
                    continue
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=user.id,
                    source_name="user_id",
                    source_id=user.id,
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

    async def validate(self, start_idx):
        raise NotImplementedError("The validate method is not implemented yet.")
