# FastAPI & Python Built-ins
from fastapi import Request
from pydantic import ValidationError
from datetime import datetime
import json

# Interfaces
from core.iControllers.iTaskController import ITaskController
from core.iServices.iTaskService import ITaskService
from core.iLoggers.iBaseLogger import IBaseLogger

# Utilities & Handlers
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser
from core.utils.validator import Validator
from core.utils.timezoneHandler import TimezoneHandler

# Entities, DTOs & Models
from core.entities.task import Task
from core.dtos.taskDtos import (
    TaskCreateDto,
    TaskUpdateDto,
    TaskResponseDto,
    TaskSearchDto,
)
from core.models.queryModel import QueryModel

class TaskController(ITaskController):
    def __init__(self, task_service: ITaskService, logger: IBaseLogger):
        self.task_service = task_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request: Request):
        try:
            task_id_str = request.path_params.get("task_id")
            if not task_id_str or not Validator.is_int(task_id_str):
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Valid Task ID is required",
                )
            
            task_id = int(task_id_str)
            
            entity_search_dto = Generator[TaskSearchDto].generate(
                TaskSearchDto, {"id": task_id, "type": "task"}
            )
            
            response = await self.task_service.find_one(
                entity_search_dto,
                [
                    "author",
                    "subject",
                    "faculty",
                    "department",
                    "year",
                ],
            )
            
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            
            task = response.data
            
            if not task or task.type == "exam":
                await self.logger.log(
                    action="FindOne",
                    entity="Task",
                    level="info",
                    code=404,
                    message="Task not found",
                    source="TaskController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Task not found",
                )
                
            # تطبيق الـ Scope الأمني 
            current_user = getattr(request.state, 'current_user', None)
            permissions = getattr(request.state, 'permissions', [])
            
            if current_user and "View Tasks" not in permissions:
                if (task.faculty_id != current_user.faculty_id or 
                    task.department_id != current_user.department_id or 
                    task.year_id != current_user.year_id):
                    return ResponseHandler.generate_response(
                        success=False, 
                        code=403, 
                        message="You are not authorized to view this task"
                    )
                
            task_mapped = Mapper[Task, TaskResponseDto].map(task, TaskResponseDto, True)
            
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=task_mapped,
            )
            
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="TaskController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request: Request):
        try:
            query = Parser.parse_query(
                request.query_params.get("query", "{}"),
                QueryModel[TaskSearchDto],
            )
            entity_search_dto = Generator[TaskSearchDto].generate_from_query(
                TaskSearchDto, query
            )
            
            entity_search_dto.type = "task"
            
            current_user = getattr(request.state, 'current_user', None)
            permissions = getattr(request.state, 'permissions', [])
            
            if current_user and "View Tasks" not in permissions:
                entity_search_dto.faculty_id = current_user.faculty_id
                entity_search_dto.department_id = current_user.department_id
                entity_search_dto.year_id = current_user.year_id

            includes = query.includes
            selects = query.selects
            is_and = query.is_and
            starts_with = query.starts_with
            is_exact = query.is_exact
            order_by = query.order_by
            descending = query.descending
            page = query.page or 1
            limit = query.limit or 50

            response = await self.task_service.find(
                entity_search_dto,
                includes,
                selects,
                is_and,
                starts_with,
                is_exact,
                order_by,
                descending,
                page,
                limit,
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            tasks = response.data
            
            if not tasks:
                await self.logger.log(
                    action="Find",
                    entity="Task",
                    level="info",
                    code=404,
                    message="Tasks not found",
                    source="TaskController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Tasks not found",
                )

            tasks_mapped = Mapper[Task, TaskResponseDto].map_list(
                tasks, TaskResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=tasks_mapped,
            )
            
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="TaskController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def search(self, request: Request):
        try:
            query = Parser.parse_query(
                request.query_params.get("query", "{}"),
                QueryModel[TaskSearchDto],
            )
            entity_search_dto = Generator[TaskSearchDto].generate_from_query(
                TaskSearchDto, query
            )
            
            
            entity_search_dto.type = "task"
            
            current_user = getattr(request.state, 'current_user', None)
            permissions = getattr(request.state, 'permissions', [])
            
            if current_user and "View Tasks" not in permissions:
                entity_search_dto.faculty_id = current_user.faculty_id
                entity_search_dto.department_id = current_user.department_id
                entity_search_dto.year_id = current_user.year_id

            includes = query.includes
            selects = query.selects
            is_and = query.is_and
            starts_with = query.starts_with
            is_exact = query.is_exact
            order_by = query.order_by
            descending = query.descending
            page = query.page or 1
            limit = query.limit or 50

            response = await self.task_service.find(
                entity_search_dto,
                includes,
                selects,
                is_and,
                starts_with,
                is_exact,
                order_by,
                descending,
                page,
                limit,
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            tasks = response.data
            
            if not tasks:
                await self.logger.log(
                    action="Search",
                    entity="Task",
                    level="info",
                    code=404,
                    message="Tasks not found",
                    source="TaskController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Tasks not found",
                )
                
            tasks_mapped = Mapper[Task, TaskResponseDto].map_list(
                tasks, TaskResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=tasks_mapped,
            )
            
        except Exception as e:
            await self.logger.log(
                action="Search",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="TaskController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
            
    async def create(self, request: Request):
        try:
            await self.task_service.begin_transaction()
            current_user = request.state.current_user
            
            try:
                payload = await request.json()
                if not isinstance(payload, dict):
                    payload = {}
            except Exception:
                payload = {}

            if not payload:
                await self.task_service.rollback_transaction()
                await self.logger.log(
                    action="Add", entity="Task", level="warning", code=400,
                    message="No Data Provided for Task Creation.",
                    details={}, source="TaskController", user_id=current_user.id
                )
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Empty Request was sent. Please provide data correctly."
                )

            if not Validator.is_sanitized(payload):
                await self.task_service.rollback_transaction()
                await self.logger.log(
                    action="Add", entity="Task", level="warning", code=400,
                    message="Un Sanitized Data Provided in The Request Body.",
                    details={}, source="TaskController", user_id=current_user.id
                )
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Invalid data provided"
                )

            payload["author_id"] = current_user.id
            payload["department_id"] = current_user.department_id
            payload["faculty_id"] = current_user.faculty_id
            payload["year_id"] = current_user.year_id
            payload["type"] = "task"

            try:
                data = Generator[TaskCreateDto].generate(TaskCreateDto, payload)
            except ValidationError as ve:
                await self.task_service.rollback_transaction()
                await self.logger.log(
                    action="Add", entity="Task", level="warning", code=400,
                    message="Validation Error in Task Creation Payload.",
                    details={"error": str(ve), "payload": payload}, source="TaskController", user_id=current_user.id
                )
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Validation Error: Ensure all required fields are provided correctly."
                )
            
            response = await self.task_service.create(data)
            
            if not response.success:
                await self.task_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )

            await self.task_service.commit_transaction()
            
            response_data = response.data
            if hasattr(response_data, "model_dump"):
                response_data = response_data.model_dump()
                
            return ResponseHandler.generate_response(
                success=True, 
                code=201, 
                message="Task created successfully", 
                data=response_data
            )

        except Exception as e:
            await self.task_service.rollback_transaction()
            await self.logger.log(
                action="Add", entity="Task", level="error", code=500,
                message="An Error Occurred while Creating Task.",
                details={"error": str(e)}, source="TaskController",
                user_id=request.state.current_user.id if hasattr(request.state, 'current_user') else None
            )
            return ResponseHandler.generate_response(
                success=False, code=500, message="An error occurred while creating task"
            )

    async def update(self, request: Request):
        try:
            await self.task_service.begin_transaction()
            current_user = request.state.current_user
            
            task_id_str = request.path_params.get("task_id")
            if not task_id_str or not Validator.is_int(task_id_str):
                await self.task_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Valid Task ID is required."
                )
            task_id = int(task_id_str)

            try:
                payload = await request.json()
                if not isinstance(payload, dict):
                    payload = {}
            except Exception:
                payload = {}

            if not payload:
                await self.task_service.rollback_transaction()
                await self.logger.log(
                    action="Edit", entity="Task", level="warning", code=400,
                    message="No Data Provided for Task Update.",
                    details={}, source="TaskController", user_id=current_user.id
                )
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Empty Request was sent. Please provide data correctly."
                )

            if not Validator.is_sanitized(payload):
                await self.task_service.rollback_transaction()
                await self.logger.log(
                    action="Edit", entity="Task", level="warning", code=400,
                    message="Un Sanitized Data Provided in The Request Body.",
                    details={}, source="TaskController", user_id=current_user.id
                )
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Invalid data provided"
                )

            payload["type"] = "task" 

            try:
                data = Generator[TaskUpdateDto].generate(TaskUpdateDto, payload)
            except ValidationError as ve:
                await self.task_service.rollback_transaction()
                await self.logger.log(
                    action="Edit", entity="Task", level="warning", code=400,
                    message="Validation Error in Task Update Payload.",
                    details={"error": str(ve), "payload": payload}, source="TaskController", user_id=current_user.id
                )
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Validation Error: Ensure fields are provided correctly."
                )
            
            response = await self.task_service.update(task_id, data)
            
            if not response.success:
                await self.task_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )

            await self.task_service.commit_transaction()
            
            response_data = response.data
            if hasattr(response_data, "model_dump"):
                response_data = response_data.model_dump()
                
            return ResponseHandler.generate_response(
                success=True, 
                code=200, 
                message="Task updated successfully", 
                data=response_data
            )

        except Exception as e:
            await self.task_service.rollback_transaction()
            await self.logger.log(
                action="Edit", entity="Task", level="error", code=500,
                message="An Error Occurred while Updating Task.",
                details={"error": str(e)}, source="TaskController",
                user_id=request.state.current_user.id if hasattr(request.state, 'current_user') else None
            )
            return ResponseHandler.generate_response(
                success=False, code=500, message="An error occurred while updating task"
            )

    async def delete(self, request: Request):
        try:
            await self.task_service.begin_transaction()
            
            task_id_str = request.path_params.get("task_id")
            if not task_id_str or not Validator.is_int(task_id_str):
                await self.task_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Valid Task ID is required."
                )
            task_id = int(task_id_str)

            response = await self.task_service.delete(task_id)
            
            if not response.success:
                await self.task_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=response.code, message=response.message
                )

            await self.task_service.commit_transaction()
            
            return ResponseHandler.generate_response(
                success=True, code=200, message="Task deleted successfully"
            )

        except Exception as e:
            await self.task_service.rollback_transaction()
            await self.logger.log(
                action="Delete", entity="Task", level="error", code=500,
                message="An Error Occurred while Deleting Task.",
                details={"error": str(e)}, source="TaskController",
                user_id=request.state.current_user.id if hasattr(request.state, 'current_user') else None
            )
            return ResponseHandler.generate_response(
                success=False, code=500, message="An error occurred while deleting task"
            )