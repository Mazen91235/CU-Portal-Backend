import os
import math
from datetime import datetime
from typing import cast
from fastapi import Request
from core.iServices.iTaskService import ITaskService
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository

from core.entities.task import Task
from core.entities.user import User
from core.entities.subject import Subject
from core.entities.role import Role
from core.dtos.baseDtos import BaseResponseDto
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.validator import Validator
from core.utils.mapper import Mapper


class TaskService(ITaskService):
    def __init__(
        self,
        task_repository: IBaseRepository[Task],
        subject_repository: IBaseRepository[Subject],
        logger: IBaseLogger,
        helper_service: IHelperService,
        role_repository: IBaseRepository[Role],
        notification_service=None, 
    ):
        self.task_repository = task_repository
        self.subject_repository = subject_repository
        self.logger = logger
        self.helper_service = helper_service
        self.role_repository = role_repository
        self.notification_service = notification_service 

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
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message
                )
            
            task = result.data

            if task:
                current_user = await self.helper_service.get_logged_in_user()
                permissions = await self.role_repository.get_user_permissions(current_user.role_id)
                
                if "View Tasks" not in permissions:
                    if (task.faculty_id != current_user.faculty_id or 
                        task.department_id != current_user.department_id or 
                        task.year_id != current_user.year_id):
                        return BaseResponseDto(
                            success=False, 
                            code=403, 
                            data=None,
                            message="You are not authorized to view this task"
                        )

            return BaseResponseDto(
                success=True,
                code=200,
                data=result.data
            )

        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Task",
                level="error",
                code=500,
                message="Error finding task",
                details={"error": str(ex)},
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
            current_user = await self.helper_service.get_logged_in_user()
            permissions = await self.role_repository.get_user_permissions(current_user.role_id)
            
            if current_user and "View Tasks" not in permissions:
                data.faculty_id = current_user.faculty_id
                data.department_id = current_user.department_id
                data.year_id = current_user.year_id
            predicate = self.helper_service.generate_dynamic_predicate(
                Task, data, ["name"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(Task, includes)
            dynamic_selects = self.helper_service.generate_dynamic_selects("Task", selects)
            dynamic_order_by = self.helper_service.generate_dynamic_order_by("Task", order_by)

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
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message
            )

            return BaseResponseDto(success=True, code=200, data=result.data)

        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while finding tasks",
                details={"error": str(ex)},
                source="TaskService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding tasks"
            )

   
    async def create(self, data):
        urls_to_cleanup = []
        
        try:
            files = []
            urls = data.urls or []
            api_key = os.environ.get("GOOGLE_TOKEN_API_KEY")

            for url in urls:
                drive_id = self.helper_service.get_drive_id(url)
                file_response = await self.helper_service.fetch_public_drive(
                    drive_id,
                    api_key,
                )
                
                if not file_response.success or not file_response.data:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid File provided",
                    )
                
                files.append(file_response.data)
                urls_to_cleanup.append(url)

            subject_response = await self.subject_repository.find_one(
                predicate=(Subject.id == data.subject_id)
            )
            
            if not subject_response.success:
                return BaseResponseDto(
                    success=False,
                    code=subject_response.code,
                    data=None,
                    message=subject_response.message,
                )

            if not data.details:
                data.details = {}
            data.details["files_data"] = files if files else []
            
            if data.links:
                data.links = [{"url": link} for link in data.links]
            
            create_res = await self.task_repository.create(data)
            
            if not create_res.success:
                for url in urls_to_cleanup:
                    try:
                        await self.helper_service.remove_file_from_drive(url)
                    except Exception:
                        pass
                return BaseResponseDto(
                    success=False,
                    code=create_res.code,
                    data=None,
                    message=create_res.message,
                )
            
            created_task = create_res.data
            
            if not created_task:
                await self.logger.log(
                    action="Create",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to create task without a specific error",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating task",
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
            )

        except Exception as ex:
            if urls_to_cleanup:
                for url in urls_to_cleanup:
                    try:
                        await self.helper_service.remove_file_from_drive(url)
                    except Exception:
                        pass
                    
            await self.logger.log(
                action="Create",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while creating task",
                details={"error": str(ex)},
                source="TaskService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating task",
            )
    async def update(self, data):
        new_urls_to_cleanup = []
        old_urls_to_remove = []
        
        try:
            target_res = await self.task_repository.find_one(
                Task.id == data.id
            )
            
            if not target_res.success:
                return BaseResponseDto(
                    success=False,
                    code=target_res.code,
                    data=None,
                    message=target_res.message,
                )
            
            target_task = target_res.data
            if not target_task:
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="info",
                    code=404,
                    message="Task not found",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Task not found",
                )

            if data.subject_id is not None:
                subject_response = await self.subject_repository.find_one(
                    Subject.id == data.subject_id
                )
                if not subject_response.success or not subject_response.data:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Subject not found",
                    )
                target_task.subject_id = subject_response.data.id

            task_details = target_task.details or {}
            
            if data.urls is not None:
                urls = data.urls
                files = []
                api_key = os.environ.get("GOOGLE_TOKEN_API_KEY")
                existing_urls = target_task.urls or []
                
                old_urls_to_remove = [u for u in existing_urls if u not in urls]

                for url in urls:
                    drive_id = self.helper_service.get_drive_id(url)
                    file_response = await self.helper_service.fetch_public_drive(
                        drive_id, 
                        api_key,
                    )
                    
                    if not file_response.success or not file_response.data:
                        return BaseResponseDto(
                            success=False,
                            code=400,
                            data=None,
                            message="Invalid File provided from Drive",
                        )
                    
                    files.append(file_response.data.get("data"))
                    
                    if url not in existing_urls:
                        new_urls_to_cleanup.append(url)
                
                target_task.urls = urls
                task_details["files_data"] = files

            if data.links is not None:
                target_task.links = [link.model_dump() for link in data.links]
            if data.name is not None: 
                target_task.name = data.name
            if data.deadline is not None: 
                target_task.deadline = data.deadline
            if data.due_date is not None: 
                target_task.due_date = data.due_date
            if data.url is not None: 
                target_task.url = data.url
            if data.details is not None and data.details.description is not None:
                task_details["description"] = data.details.description

            target_task.details = task_details

            update_res = await self.task_repository.update(target_task)
            
            if not update_res.success:
                for url in new_urls_to_cleanup:
                    try:
                        await self.helper_service.remove_file_from_drive(url)
                    except Exception:
                        pass
                return BaseResponseDto(
                    success=False,
                    code=update_res.code,
                    data=None,
                    message=update_res.message,
                )

            updated_task = update_res.data
            
            if not updated_task:
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to update task without a specific error",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating task",
                )
            
            for old_url in old_urls_to_remove:
                try:
                    await self.helper_service.remove_file_from_drive(old_url)
                except Exception as e:
                    await self.logger.log(
                        action="Update",
                        entity="Task",
                        level="warning",
                        code=500,
                        message="Task updated successfully but failed to remove old file from Drive",
                        details={"url": old_url, "error": str(e)},
                        source="TaskService",
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
            )

        except Exception as ex:
            if new_urls_to_cleanup:
                for url in new_urls_to_cleanup:
                    try:
                        await self.helper_service.remove_file_from_drive(url)
                    except Exception:
                        pass
                    
            await self.logger.log(
                action="Update",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while updating task",
                details={"error": str(ex)},
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
            result = await self.task_repository.find_one(
                predicate=(Task.id == data.id)
            )
            
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            
            task = result.data
            if not task:
                await self.logger.log(
                    action="Delete",
                    entity="Task",
                    level="info",
                    code=404,
                    message="Task not found",
                    source="TaskService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Task not found",
                )

            delete_res = await self.task_repository.delete(task)
            
            if not delete_res.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_res.code,
                    data=None,
                    message=delete_res.message,
                )

            urls = task.urls or []
            for url in urls:
                try:
                    await self.helper_service.remove_file_from_drive(url)
                except Exception as e:
                    await self.logger.log(
                        action="Delete", 
                        entity="Task", 
                        level="error", 
                        code=500,
                        message="Task deleted from DB, but failed to remove file from Drive", 
                        details={"url": url, "error": str(e)}, 
                        source="TaskService",
                    )

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
                data=True
            )

        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while deleting task",
                details={"error": str(ex)},
                source="TaskService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting task",
            )