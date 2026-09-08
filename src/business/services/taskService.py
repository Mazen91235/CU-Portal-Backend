from sqlalchemy import and_
from core.iServices.iTaskService import ITaskService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.task import Task
from core.entities.subject import Subject
from core.entities.notification import Notification
from core.dtos.baseDtos import BaseResponseDto
from core.utils.validator import Validator
from core.utils.timezoneHandler import TimezoneHandler


class TaskService(ITaskService):
    def __init__(
        self,
        task_repository: IBaseRepository[Task],
        subject_repository: IBaseRepository[Subject],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.task_repository = task_repository
        self.subject_repository = subject_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions

    async def begin_transaction(self):
        await self.task_repository.begin_transaction()

    async def commit_transaction(self):
        await self.task_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.task_repository.rollback_transaction()

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
                Task, data, ["name"], is_and, starts_with, is_exact
            )
            predicate = (
                and_(predicate, Task.task_type == "task")
                if predicate is not None
                else Task.task_type == "task"
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Task, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Task", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Task", order_by
            )
            result = await self.task_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
            )

            if not result.success:
                return BaseResponseDto(
                    success=False, code=result.code, data=None, message=result.message
                )

            task = result.data

            return BaseResponseDto(success=True, code=200, data=task)

        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Task",
                level="error",
                code=500,
                message="Error finding task",
                details={"error": repr(ex)},
                source="TaskService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding the task",
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
                Task, data, ["name"], is_and, starts_with, is_exact
            )
            predicate = (
                and_(predicate, Task.task_type == "task")
                if predicate is not None
                else Task.task_type == "task"
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Task, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Task", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Task", order_by
            )
            result = await self.task_repository.find(
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
                    success=False, code=result.code, data=None, message=result.message
                )
            tasks = result.data
            return BaseResponseDto(
                success=True, code=200, data=tasks, next_page=result.next_page
            )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while finding tasks",
                details={"error": repr(ex)},
                source="TaskService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding tasks",
            )

    async def create(self, data):
        try:
            existing_task_response = await self.task_repository.find_one(
                and_(
                    Task.name == data.name,
                    Task.task_type == "task",
                    Task.subject_id == data.subject_id,
                )
            )
            if not existing_task_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_task_response.code,
                    data=None,
                    message=existing_task_response.message,
                )
            existing_task = existing_task_response.data
            if existing_task:
                await self.logger.log(
                    action="Create",
                    entity="Task",
                    level="warning",
                    code=400,
                    message="Task with the same name already exists for this subject.",
                    details={"name": data.name, "subject_id": data.subject_id},
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Task with the same name already exists for this subject.",
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
                    entity="Task",
                    level="warning",
                    code=404,
                    message="Subject not found for Task Creation.",
                    details={"subject_id": data.subject_id},
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Subject not found",
                )
            if data.url and not Validator.is_valid_external_url(data.url):
                await self.logger.log(
                    action="Create",
                    entity="Task",
                    level="warning",
                    code=400,
                    message="Invalid Submission URL provided for Task Creation.",
                    details={"url": data.url},
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Invalid Submission URL provided: {data.url}",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Task Creation.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating task",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Create",
                    entity="Task",
                    level="error",
                    code=500,
                    message="No logged-in user found for Task Creation.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating task",
                )
            data.author_id = logged_in_user.id
            data.due_date = (
                TimezoneHandler.to_date(data.deadline) if data.deadline else None
            )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=data.subject_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Task",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user {logged_in_user.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to create task for the specified criteria.",
                )
            data.details = {} if not data.details else data.details
            urls = data.details.get("urls", [])
            links = data.details.get("links", [])
            data.details.pop("urls", None)
            data.details.pop("links", None)
            data.task_type = "task"
            create_task_response = await self.task_repository.create(data)
            if not create_task_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_task_response.code,
                    data=None,
                    message=create_task_response.message,
                )
            created_task = create_task_response.data
            if not created_task:
                await self.logger.log(
                    action="Create",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to create task without a specific error.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating task",
                )
            for url in urls:
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=logged_in_user.id,
                    source_name="task_id",
                    source_id=created_task.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Task",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for task.",
                        details={"url": url},
                        source="TaskService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code or 500,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Create",
                        entity="Task",
                        level="error",
                        code=500,
                        message="Failed to create attachment for task without a specific error.",
                        details={"url": url},
                        source="TaskService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating task",
                    )
            for link in links:
                link_name = link.get("name", link.get("title", ""))
                link_url = link.get("url", "")
                attachment_response = await self.helper_service.create_attachment(
                    is_file=False,
                    url=link_url,
                    author_id=logged_in_user.id,
                    source_name="task_id",
                    source_id=created_task.id,
                    link_title=link_name,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Task",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for task.",
                        details={"url": link_url},
                        source="TaskService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code or 500,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Create",
                        entity="Task",
                        level="error",
                        code=500,
                        message="Failed to create attachment for task without a specific error.",
                        details={"url": link_url},
                        source="TaskService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating task",
                    )
            share_link = f"/users/tasks/{created_task.id}"
            await self.helper_service.send_notification(
                Notification.NotificationType.TASK,
                created_task.id,
                f"New task '{created_task.name}' has been created for subject {subject.name}.",
                share_link,
                subject_id=created_task.subject_id,
            )
            await self.logger.log(
                action="Create",
                entity="Task",
                level="info",
                code=201,
                message="Task created successfully",
                source="TaskService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_task,
                message="Task created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while creating task",
                details={"error": repr(ex)},
                source="TaskService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating task",
            )

    async def update(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Task, ["attachments"]
            )
            target_task_response = await self.task_repository.find_one(
                and_(Task.id == data.id, Task.task_type == "task"), dynamic_includes
            )
            if not target_task_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_task_response.code,
                    data=None,
                    message=target_task_response.message,
                )
            target_task = target_task_response.data
            if not target_task:
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="info",
                    code=404,
                    message="Task not found for update",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Task not found",
                )
            existing_task_response = await self.task_repository.find_one(
                and_(
                    Task.name == data.name,
                    Task.task_type == "task",
                    Task.subject_id == data.subject_id,
                )
            )
            if not existing_task_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_task_response.code,
                    data=None,
                    message=existing_task_response.message,
                )
            existing_task = existing_task_response.data
            if existing_task and existing_task.id != data.id:
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="warning",
                    code=400,
                    message="Another task with the same name already exists for this subject.",
                    details={"name": data.name, "subject_id": data.subject_id},
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Another task with the same name already exists for this subject.",
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
                    entity="Task",
                    level="warning",
                    code=404,
                    message="Subject not found for Task Update.",
                    details={"subject_id": data.subject_id},
                    source="TaskService",
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
                    action="Update",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Task Update.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating task",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="error",
                    code=500,
                    message="No logged-in user found for Task Update.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating task",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=data.subject_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user {logged_in_user.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to update task for the specified criteria.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Task Update.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating task",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Task Update.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating task",
                )
            if (
                logged_in_user.id != target_task.author_id
                and "Manage All Tasks" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="warning",
                    code=403,
                    message="User does not have permission to update this task.",
                    details={
                        "user_id": logged_in_user.id,
                        "task_id": target_task.id,
                    },
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to update this task.",
                )
            data.author_id = logged_in_user.id
            data.due_date = (
                TimezoneHandler.to_date(data.deadline) if data.deadline else None
            )
            old_attachments = target_task.attachments or set()
            if data.url and not Validator.is_valid_external_url(data.url):
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="warning",
                    code=400,
                    message="Invalid Submission URL provided for Task Update.",
                    details={"url": data.url},
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid Submission URL provided",
                )
            data.details = {} if not data.details else data.details
            urls = data.details.get("urls", [])
            links = data.details.get("links", [])
            data.details.pop("urls", None)
            data.details.pop("links", None)
            target_task.name = data.name
            target_task.deadline = data.deadline
            target_task.due_date = data.due_date
            target_task.subject_id = data.subject_id
            target_task.url = data.url
            target_task.details = data.details
            target_task.author_id = data.author_id
            update_response = await self.task_repository.update(target_task)
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_task = update_response.data
            if not updated_task:
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to update task without a specific error.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating task",
                )
            new_urls = [
                u
                for u in urls
                if u not in [a.url for a in old_attachments if a.is_file]
            ]
            new_links = [
                l
                for l in links
                if l.get("url", "")
                not in [a.url for a in old_attachments if not a.is_file]
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
                    source_name="task_id",
                    source_id=updated_task.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Task",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for task.",
                        details={"url": url},
                        source="TaskService",
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
                        action="Update",
                        entity="Task",
                        level="error",
                        code=500,
                        message="Failed to create attachment for task without a specific error.",
                        details={"url": url},
                        source="TaskService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating task",
                    )
            for link in new_links:
                link_name = link.get("name", link.get("title", ""))
                link_url = link.get("url", "")
                attachment_response = await self.helper_service.create_attachment(
                    is_file=False,
                    url=link_url,
                    author_id=logged_in_user.id,
                    source_name="task_id",
                    source_id=updated_task.id,
                    link_title=link_name,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Task",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for task.",
                        details={"url": link_url},
                        source="TaskService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code or 500,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Update",
                        entity="Task",
                        level="error",
                        code=500,
                        message="Failed to create attachment for task without a specific error.",
                        details={"url": link_url},
                        source="TaskService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating task",
                    )
            share_link = f"/users/tasks/{updated_task.id}"
            await self.helper_service.send_notification(
                Notification.NotificationType.TASK,
                updated_task.id,
                f"Task '{updated_task.name}' has been updated for subject {subject.name}.",
                share_link,
                subject_id=updated_task.subject_id,
            )
            await self.logger.log(
                action="Update",
                entity="Task",
                level="info",
                code=200,
                message="Task updated successfully",
                source="TaskService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_task,
                message="Task updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while updating task",
                details={"error": repr(ex)},
                source="TaskService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating task",
            )

    async def delete(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Task, ["attachments"]
            )
            target_task_response = await self.task_repository.find_one(
                and_(Task.id == data.id, Task.task_type == "task"), dynamic_includes
            )
            if not target_task_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_task_response.code,
                    data=None,
                    message=target_task_response.message,
                )
            target_task = target_task_response.data
            if not target_task:
                await self.logger.log(
                    action="Delete",
                    entity="Task",
                    level="warning",
                    code=404,
                    message="Task not found for deletion",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Task not found",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Task Deletion.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting task",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Delete",
                    entity="Task",
                    level="error",
                    code=500,
                    message="No logged-in user found for Task Deletion.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting task",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=data.subject_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Task",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user {logged_in_user.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to delete task for the specified criteria.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Task Delete.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting task",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Delete",
                    entity="Task",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Task Delete.",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting task",
                )
            if (
                logged_in_user.id != target_task.author_id
                and "Manage All Tasks" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Delete",
                    entity="Task",
                    level="warning",
                    code=403,
                    message="User does not have permission to delete this task.",
                    details={
                        "user_id": logged_in_user.id,
                        "task_id": target_task.id,
                    },
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to delete this task.",
                )
            to_be_removed_attachments = target_task.attachments or set()
            delete_response = await self.task_repository.delete(target_task)
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
                entity="Task",
                level="info",
                code=200,
                message="Task deleted successfully",
                source="TaskService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Task deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while deleting task",
                details={"error": repr(ex)},
                source="TaskService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting task",
            )
