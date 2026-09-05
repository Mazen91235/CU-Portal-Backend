from typing import cast
from core.iControllers.iTaskController import ITaskController
from core.iServices.iTaskService import ITaskService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.task import Task
from core.dtos.taskDtos import (
    TaskCreateDto,
    TaskUpdateDto,
    TaskResponseDto,
    TaskSearchDto,
    TaskDeleteDto,
)


class TaskController(ITaskController):
    def __init__(self, task_service: ITaskService, logger: IBaseLogger):
        self.task_service = task_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[TaskSearchDto].generate(
                TaskSearchDto, {"id": id}
            )

            response = await self.task_service.find_one(
                entity_search_dto,
                [
                    "author",
                    "subject",
                    "faculty",
                    "department",
                    "year",
                    "attachments",
                ],
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            task = response.data

            if not task:
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
                details={"error": repr(e)},
                source="TaskController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[TaskSearchDto].generate_from_query(
                TaskSearchDto, query
            )

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

            tasks_mapped = Mapper[Task, TaskResponseDto].map_list(
                tasks or [], TaskResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=tasks_mapped,
                next_page=response.next_page,
            )

        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="TaskController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.task_service.begin_transaction()
            task = Mapper[TaskCreateDto, Task].map(data, Task)

            response = await self.task_service.create(task)

            if not response.success:
                await self.task_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            created_task = response.data
            if not created_task:
                await self.task_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to create task",
                    details={},
                    source="TaskController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create task",
                )

            task_mapped = Mapper[Task, TaskResponseDto].map(
                created_task, TaskResponseDto, True
            )

            await self.task_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=task_mapped,
                message="Task created successfully",
            )

        except Exception as e:
            await self.task_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="TaskController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, id, data):
        try:
            await self.task_service.begin_transaction()
            task = cast(Task, Mapper[TaskUpdateDto, Task].map(data, Task))
            task.id = id

            response = await self.task_service.update(task)

            if not response.success:
                await self.task_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_task = response.data
            if not updated_task:
                await self.task_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Task",
                    level="error",
                    code=500,
                    message="Failed to update task",
                    details={},
                    source="TaskController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to update task",
                )
            task_mapped = Mapper[Task, TaskResponseDto].map(
                updated_task, TaskResponseDto, True
            )

            await self.task_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=task_mapped,
                message="Task updated successfully",
            )

        except Exception as e:
            await self.task_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="TaskController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            await self.task_service.begin_transaction()
            data = Generator[TaskDeleteDto].generate(TaskDeleteDto, {"id": id})
            entity = Mapper[TaskDeleteDto, Task].map(data, Task)

            response = await self.task_service.delete(entity)

            if not response.success:
                await self.task_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.task_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Task deleted successfully",
            )

        except Exception as e:
            await self.task_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Task",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="TaskController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
