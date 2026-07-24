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
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.taskDtos import (
    TaskCreateDto,
    TaskUpdateDto,
    TaskResponseDto,
    TaskSearchDto,
)
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
        notification_service=None, 
    ):
        self.task_repository = task_repository
        self.subject_repository = subject_repository
        self.logger = logger
        self.helper_service = helper_service
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
                Task, data, ["name", "type"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(Task, includes)
            dynamic_selects = self.helper_service.generate_dynamic_selects("Task", selects)
            dynamic_order_by = self.helper_service.generate_dynamic_order_by("Task", order_by)

            result = await self.task_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
            )

            if not result.success:
                return BaseResponseDto(success=False, code=result.code, data=None, message=result.message)

            return BaseResponseDto(success=True, code=200, data=result.data)

        except Exception as ex:
            await self.logger.log(
                action="FindOne", entity="Task", level="error", code=500,
                message="Error finding task", details={"error": str(ex)}, source="TaskService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while finding the task")


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
                Task, data, ["name", "type"], is_and, starts_with, is_exact
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
                return BaseResponseDto(success=False, code=result.code, data=None, message=result.message)

            return BaseResponseDto(success=True, code=200, data=result.data)

        except Exception as ex:
            await self.logger.log(
                action="Find", entity="Task", level="error", code=500,
                message="An error occurred while finding tasks", details={"error": str(ex)}, source="TaskService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while finding tasks")

   
    async def create(self, data: TaskCreateDto) -> BaseResponseDto:
        current_user = None
        urls_to_cleanup = []
        try:
            request = await self.helper_service.get_current_request()
            
            if request and hasattr(request.state, "current_user"):
                current_user = request.state.current_user
            else:
                user_response = await self.helper_service.get_logged_in_user()
                current_user = user_response.data if user_response and user_response.success else None

            if not current_user:
                return BaseResponseDto(success=False, code=401, data=None, message="Unauthorized")

            files = []
            urls = data.urls or []
            api_key = os.environ.get("GOOGLE_TOKEN_API_KEY")

            for url in urls:
                if not Validator.is_drive_url(url):
                    return BaseResponseDto(success=False, code=400, data=None, message="Invalid File provided")

                drive_id = self.helper_service.get_drive_id(url)
                file_response = await self.helper_service.fetch_public_drive(drive_id, api_key, request)
                
                if not file_response.success or not file_response.data:
                    return BaseResponseDto(success=False, code=400, data=None, message="Invalid File provided")
                
                file_data = file_response.data.get("data") if isinstance(file_response.data, dict) else file_response.data
                files.append(file_data)
                urls_to_cleanup.append(url)

            links = data.links or []
            for link in links:
                link_url = getattr(link, "url", None) or (link.get("url") if isinstance(link, dict) else None)
                if not link_url or not Validator.is_valid_url(link_url): 
                    return BaseResponseDto(success=False, code=400, data=None, message="Invalid Link provided")

            if data.url and not Validator.is_valid_url(data.url):
                return BaseResponseDto(success=False, code=400, data=None, message="Invalid submission URL provided")

            subject_response = await self.subject_repository.find_one(Subject.id == data.subject_id)
            subject = subject_response.data if subject_response.success else None

            user_faculty = getattr(current_user, 'faculty_id', None)
            user_dept = getattr(current_user, 'department_id', None)
            user_year = getattr(current_user, 'year_id', None)

            if (not subject or 
                subject.faculty_id != user_faculty or 
                subject.department_id != user_dept or 
                subject.year_id != user_year):
                
                return BaseResponseDto(success=False, code=404, data=None, message="Subject not found in your criteria")

            task_details = data.details or {}
            if hasattr(task_details, "model_dump"):
                task_details = task_details.model_dump()
            elif not isinstance(task_details, dict):
                task_details = dict(task_details)

            task_details["files_data"] = files if files else []
            data.details = task_details

            task_entity = Mapper[TaskCreateDto, Task].map(data, Task)
            task_entity.author_id = current_user.id
            task_entity.faculty_id = user_faculty
            task_entity.department_id = user_dept
            task_entity.year_id = user_year
            task_entity.type = "task"
            
            if task_entity.links:
                task_entity.links = [link.model_dump() if hasattr(link, "model_dump") else dict(link) for link in task_entity.links]
            
            created_task_response = await self.task_repository.create(task_entity)
            
            if not created_task_response.success:
                for url in urls_to_cleanup:
                    await self.helper_service.remove_file_from_drive(url, current_user.google_refresh_token, request)
                return BaseResponseDto(success=False, code=created_task_response.code, data=None, message=created_task_response.message)
            
            created_task = created_task_response.data

            if self.notification_service and created_task.deadline:
                try:
                    utc_now = TimezoneHandler.now("UTC")
                    diff_days = math.ceil((created_task.deadline.date() - utc_now.date()).total_seconds() / 86400)
                    diff_string = (
                        f"due in {diff_days} day{'s' if diff_days > 1 else ''}" if diff_days > 0
                        else ("due today" if diff_days == 0 else f"was due {-diff_days} day{'s' if diff_days < -1 else ''} ago")
                    )
                    
                    notification_message = f'New task "{created_task.name}" has been assigned for subject "{subject.name}". {diff_string}.'
                    frontend_base = os.environ.get('FRONTEND_URL', '')
                    notification_url = f"{frontend_base}/user/tasks/{created_task.id}"
                    
                    await self.notification_service.create_notification(
                        request=request, type="task", entity_id=created_task.id, 
                        message=notification_message, url=notification_url
                    )
                except Exception:
                    pass

            response_dto = Mapper[Task, TaskResponseDto].map(created_task, TaskResponseDto)
            
            return BaseResponseDto(success=True, code=201, data=response_dto)

        except Exception as ex:
            if current_user and urls_to_cleanup:
                for url in urls_to_cleanup:
                    try:
                        await self.helper_service.remove_file_from_drive(url, current_user.google_refresh_token, request)
                    except: pass
                    
            await self.logger.log(
                action="Add", entity="Task", level="error", code=500,
                message="An Error Occurred while Creating Task.", details={"error": str(ex)}, source="TaskService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while creating task")

    async def update(self, task_id: int, data: TaskUpdateDto) -> BaseResponseDto[TaskResponseDto]:
        current_user = None
        new_urls_to_cleanup = []
        old_urls_to_remove = []
        try:
            request = await self.helper_service.get_current_request()
            
            if request and hasattr(request.state, "current_user"):
                current_user = request.state.current_user
            else:
                user_response = await self.helper_service.get_logged_in_user()
                current_user = user_response.data if user_response and user_response.success else None

            if not current_user:
                return BaseResponseDto(success=False, code=401, data=None, message="Unauthorized")

            existing_task_response = await self.task_repository.find_one(Task.id == task_id)
            existing_task = existing_task_response.data if existing_task_response.success else None
            
            if not existing_task or existing_task.type == "exam":
                return BaseResponseDto(success=False, code=404, data=None, message="Task not found")

            user_permissions = getattr(request.state, 'permissions', [])
            if not user_permissions:
                user_permissions = await self.helper_service.get_user_permissions(request) or []

            if existing_task.author_id != current_user.id and "Manage Tasks" not in user_permissions:
                return BaseResponseDto(success=False, code=403, data=None, message="You are not authorized to update this task")

            user_faculty = getattr(current_user, 'faculty_id', None)
            user_dept = getattr(current_user, 'department_id', None)
            user_year = getattr(current_user, 'year_id', None)

            if data.subject_id is not None:
                subject_response = await self.subject_repository.find_one(Subject.id == data.subject_id)
                subject = subject_response.data if subject_response.success else None

                if not subject or subject.faculty_id != user_faculty or subject.department_id != user_dept or subject.year_id != user_year:
                    return BaseResponseDto(success=False, code=404, data=None, message="Subject not found in your criteria")
                
                existing_task.subject_id = subject.id
            else:
                subject_response = await self.subject_repository.find_one(Subject.id == existing_task.subject_id)
                subject = subject_response.data if subject_response.success else None

            task_details = existing_task.details if isinstance(existing_task.details, dict) else dict(existing_task.details or {})
            
            if data.urls is not None:
                urls = data.urls
                files = []
                api_key = os.environ.get("GOOGLE_TOKEN_API_KEY")
                existing_urls = existing_task.urls or []

                old_urls_to_remove = [u for u in existing_urls if u not in urls]

                for url in urls:
                    if not Validator.is_drive_url(url):
                        return BaseResponseDto(success=False, code=400, data=None, message="Invalid File provided")

                    drive_id = self.helper_service.get_drive_id(url)
                    file_response = await self.helper_service.fetch_public_drive(drive_id, api_key, request)
                    
                    if not file_response.success or not file_response.data:
                        return BaseResponseDto(success=False, code=400, data=None, message="Invalid File provided")
                    
                    file_data = file_response.data.get("data") if isinstance(file_response.data, dict) else file_response.data
                    files.append(file_data)
                    
                    if url not in existing_urls:
                        new_urls_to_cleanup.append(url)
                
                existing_task.urls = urls
                task_details["files_data"] = files

            if data.links is not None:
                links = data.links
                for link in links:
                    link_url = getattr(link, "url", None) or (link.get("url") if isinstance(link, dict) else None)
                    if not link_url or not Validator.is_valid_url(link_url): 
                        return BaseResponseDto(success=False, code=400, data=None, message="Invalid Link provided")
                existing_task.links = [link.model_dump() if hasattr(link, "model_dump") else dict(link) for link in links]

            if data.name is not None: existing_task.name = data.name
            if data.deadline is not None: existing_task.deadline = data.deadline
            if data.due_date is not None: existing_task.due_date = data.due_date
            if data.url is not None: 
                if data.url and not Validator.is_valid_url(data.url):
                    return BaseResponseDto(success=False, code=400, data=None, message="Invalid submission URL provided")
                existing_task.url = data.url
                
            if hasattr(data, "details") and data.details is not None:
                new_desc = getattr(data.details, "description", None) or (data.details.get("description") if isinstance(data.details, dict) else None)
                if new_desc is not None:
                    task_details["description"] = new_desc

            existing_task.details = task_details

            update_response = await self.task_repository.update(existing_task)
            
            if not update_response.success:
                for url in new_urls_to_cleanup:
                    await self.helper_service.remove_file_from_drive(url, current_user.google_refresh_token, request)
                return BaseResponseDto(success=False, code=update_response.code, data=None, message=update_response.message)

            for old_url in old_urls_to_remove:
                try:
                    await self.helper_service.remove_file_from_drive(old_url, current_user.google_refresh_token, request)
                except Exception as e:
                    await self.logger.log(
                        action="Edit", entity="Task", level="warning", code=500,
                        message="Task updated successfully but failed to remove old file from Drive", 
                        details={"url": old_url, "error": str(e)}, source="TaskService",
                    )

            updated_task = update_response.data

            if self.notification_service and subject and updated_task.deadline:
                try:
                    utc_now = TimezoneHandler.now("UTC")
                    diff_days = math.ceil((updated_task.deadline.date() - utc_now.date()).total_seconds() / 86400)
                    diff_string = (
                        f"due in {diff_days} day{'s' if diff_days > 1 else ''}" if diff_days > 0
                        else ("due today" if diff_days == 0 else f"was due {-diff_days} day{'s' if diff_days < -1 else ''} ago")
                    )
                    
                    notification_message = f'Task "{updated_task.name}" has been updated for subject "{subject.name}". {diff_string}.'
                    frontend_base = os.environ.get('FRONTEND_URL', '')
                    notification_url = f"{frontend_base}/user/tasks/{updated_task.id}"
                    
                    await self.notification_service.create_notification(
                        request=request, type="task", entity_id=updated_task.id, 
                        message=notification_message, url=notification_url
                    )
                except Exception:
                    pass

            response_dto = Mapper[Task, TaskResponseDto].map(updated_task, TaskResponseDto)
            
            return BaseResponseDto(success=True, code=200, data=response_dto)

        except Exception as ex:
            if current_user and new_urls_to_cleanup:
                for url in new_urls_to_cleanup:
                    try:
                        await self.helper_service.remove_file_from_drive(url, current_user.google_refresh_token, request)
                    except: pass
                    
            await self.logger.log(
                action="Edit", entity="Task", level="error", code=500,
                message="An Error Occurred while Updating Task.", details={"error": str(ex)}, source="TaskService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while updating task")

    async def delete(self, task_id: int) -> BaseResponseDto[bool]:
        current_user = None  
        try:
            request = await self.helper_service.get_current_request()
            user_response = await self.helper_service.get_logged_in_user()
            
            if not user_response.success or not user_response.data:
                return BaseResponseDto(success=False, code=401, data=None, message="Unauthorized")
                
            current_user = user_response.data

            task_response = await self.task_repository.find_one(Task.id == task_id)
            if not task_response.success or not task_response.data:
                return BaseResponseDto(success=False, code=404, data=None, message="Task not found")

            task = task_response.data
            
            if task.type == "exam":
                return BaseResponseDto(success=False, code=404, data=None, message="Task not found")

            user_permissions = getattr(request.state, 'permissions', [])
            if not user_permissions:
                user_permissions = await self.helper_service.get_user_permissions(request) or []

            is_author = task.author_id == current_user.id
            is_admin = "Manage Tasks" in user_permissions
            
            if not is_author and not is_admin:
                return BaseResponseDto(success=False, code=403, data=None, message="You are not authorized to delete this task")

            delete_response = await self.task_repository.delete(task)
            
            if not delete_response.success:
                return BaseResponseDto(success=False, code=delete_response.code, data=None, message=delete_response.message)

            urls = task.urls or []
            for url in urls:
                try:
                    removed = await self.helper_service.remove_file_from_drive(url, current_user.google_refresh_token, request)
                    if not removed:
                        await self.logger.log(
                            action="Delete", entity="Task", level="error", code=500,
                            message="Task deleted from DB, but failed to remove file from Drive", 
                            details={"url": url}, source="TaskService", user_id=current_user.id,
                        )
                except Exception as e:
                    await self.logger.log(
                        action="Delete", entity="Task", level="error", code=500,
                        message="Exception removing file from Drive after DB delete", 
                        details={"url": url, "error": str(e)}, source="TaskService", user_id=current_user.id,
                    )

            return BaseResponseDto(success=True, code=200, message="Task deleted successfully", data=True)

        except Exception as ex:
            await self.logger.log(
                action="Delete", entity="Task", level="error", code=500,
                message="An Error Occurred while Deleting Task.", details={"error": str(ex)}, source="TaskService",
            )
            return BaseResponseDto(success=False, code=500, data=None, message="An error occurred while deleting task")