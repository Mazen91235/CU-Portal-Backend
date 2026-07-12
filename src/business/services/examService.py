import os
import math
from datetime import datetime
from sqlalchemy import and_, func
from sqlalchemy.orm import selectinload
from core.iServices.iExamService import IExamService
from core.iServices.iUserService import IUserService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.task import Task
from core.entities.subject import Subject
from core.entities.user import User
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.examDtos import ExamSearchDto, ExamCreateDto, ExamUpdateDto
from core.models.queryModel import QueryModel
from core.utils.timezoneHandler import TimezoneHandler


class ExamService(IExamService):
    def __init__(
        self,
        task_repository: IBaseRepository[Task],
        subject_repository: IBaseRepository[Subject],
        user_service: IUserService,
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.task_repository = task_repository
        self.subject_repository = subject_repository
        self.user_service = user_service
        self.logger = logger
        self.helper_service = helper_service

    async def find_one(self, predicate=None, includes=None, selects=None, order_by=None, descending=False):
        return await self.task_repository.find_one(predicate, includes, selects, order_by, descending)

    async def find(self, predicate=None, includes=None, selects=None, order_by=None, descending=False, page=1, limit=50):
        return await self.task_repository.find(predicate, includes, selects, order_by, descending, page, limit)

    async def count(self, predicate=None):
        return await self.task_repository.count(predicate)

    async def create(self, entity: Task):
        return await self.task_repository.create(entity)

    async def update(self, entity: Task, updates=None):
        return await self.task_repository.update(entity, updates)

    async def delete(self, entity: Task):
        return await self.task_repository.delete(entity)

    # Admin Specific Methods
    async def create_exam(self, data: ExamCreateDto) -> BaseResponseDto[Task]:
        try:
            current_user = (await self.helper_service.get_logged_in_user()).data

            # 1. Date Validation
            try:
                deadline_date = TimezoneHandler.from_isoformat(f"{data.due_date}T{data.start_time}")
            except ValueError:
                return BaseResponseDto(success=False, code=400, message="Invalid date or time format.")

            if deadline_date <= TimezoneHandler.now("UTC"):
                return BaseResponseDto(success=False, code=400, message="Exam Date must be a future date.")

            # 2. Subject Validation (Must belong to Admin's Faculty/Dept/Year)
            subject_response = await self.subject_repository.find_one(Subject.id == data.subject_id)
            subject = subject_response.data

            if (not subject or 
                subject.faculty_id != current_user.faculty_id or 
                subject.department_id != current_user.department_id or 
                subject.year_id != current_user.year_id):
                return BaseResponseDto(success=False, code=404, message="Subject not found in your criteria.")

            # 3. Create Task Entity
            exam = Task(
                name=data.title,
                type="exam",
                faculty_id=current_user.faculty_id,
                department_id=current_user.department_id,
                year_id=current_user.year_id,
                details={
                    "description": data.description,
                    "instructions": data.instructions,
                    "location": data.location,
                    "exam_type": data.exam_type,
                    "exam_format": data.exam_format,
                    "exam_weight": data.exam_weight,
                    "duration": float(data.duration) if data.duration else None,
                },
                deadline=deadline_date,
                due_date=deadline_date.date(),
                subject_id=subject.id,
                author_id=current_user.id,
            )

            result = await self.task_repository.create(exam)
            if not result.success:
                return result

            # 4. Send Notification
            diff_days = math.ceil((exam.deadline.date() - TimezoneHandler.now("UTC").date()).total_seconds() / 86400)
            diff_string = f"due in {diff_days} day{'s' if diff_days > 1 else ''}" if diff_days > 0 else "due today"
            
            await self.helper_service.send_notification(
                type="exam",
                parent_id=exam.id,
                content=f'New exam "{exam.name}" has been assigned for subject "{subject.name}". {diff_string}.',
                url=f"{os.environ.get('FRONTEND_URL')}/user/exams/{exam.id}"
            )

            return BaseResponseDto(success=True, code=201, data=result.data, message="Exam created successfully.")

        except Exception as ex:
            await self.logger.log("Add", "Exam", "error", 500, "Error creating exam", "ExamService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while creating exam.")

    async def update_exam(self, exam_id: int, data: ExamUpdateDto) -> BaseResponseDto[Task]:
        try:
            current_user = (await self.helper_service.get_logged_in_user()).data
            permissions = (await self.user_service.get_user_permissions()).data or []

            # 1. Fetch Existing Exam
            exam_response = await self.task_repository.find_one(
                and_(Task.id == exam_id, Task.type == "exam"),
                includes=[selectinload(Task.author), selectinload(Task.subject)]
            )
            exam = exam_response.data
            if not exam:
                return BaseResponseDto(success=False, code=404, message="Exam not found.")

            # 2. Authorization Check
            if exam.author_id != current_user.id and "Manage All Exams" not in permissions and "Manage All Tasks" not in permissions:
                return BaseResponseDto(success=False, code=403, message="You are not authorized to update this exam.")

            # 3. Date Validation
            try:
                deadline_date = TimezoneHandler.from_isoformat(f"{data.due_date}T{data.start_time}")
            except ValueError:
                return BaseResponseDto(success=False, code=400, message="Invalid date or time format.")

            if deadline_date <= TimezoneHandler.now("UTC"):
                return BaseResponseDto(success=False, code=400, message="Exam Date must be a future date.")

            # 4. Update Properties
            exam.name = data.title
            exam.deadline = deadline_date
            exam.due_date = deadline_date.date()
            exam.details["description"] = data.description
            exam.details["instructions"] = data.instructions
            exam.details["location"] = data.location
            exam.details["duration"] = float(data.duration) if data.duration else None
            exam.details["exam_format"] = data.exam_format
            exam.details["exam_weight"] = data.exam_weight
            exam.details["exam_type"] = data.exam_type
            exam.author_id = current_user.id  # Update author to latest editor

            result = await self.task_repository.update(exam)
            if not result.success:
                return result

            # 5. Send Notification
            diff_days = math.ceil((exam.deadline.date() - TimezoneHandler.now("UTC").date()).total_seconds() / 86400)
            diff_string = f"due in {diff_days} day{'s' if diff_days > 1 else ''}" if diff_days > 0 else "due today"
            
            await self.helper_service.send_notification(
                type="exam",
                parent_id=exam.id,
                content=f'Exam "{exam.name}" has been updated for subject "{exam.subject.name}". {diff_string}.',
                url=f"{os.environ.get('FRONTEND_URL')}/user/exams/{exam.id}"
            )

            return BaseResponseDto(success=True, code=200, data=result.data, message="Exam updated successfully.")

        except Exception as ex:
            await self.logger.log("Edit", "Exam", "error", 500, "Error updating exam", "ExamService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while updating exam.")

    async def delete_exam(self, exam_id: int) -> BaseResponseDto[bool]:
        try:
            current_user = (await self.helper_service.get_logged_in_user()).data
            permissions = (await self.user_service.get_user_permissions()).data or []

            exam_response = await self.task_repository.find_one(and_(Task.id == exam_id, Task.type == "exam"))
            exam = exam_response.data
            
            if not exam:
                return BaseResponseDto(success=False, code=404, message="Exam not found.")

            if exam.author_id != current_user.id and "Manage All Exams" not in permissions and "Manage All Tasks" not in permissions:
                return BaseResponseDto(success=False, code=403, message="You are not authorized to delete this exam.")

            result = await self.task_repository.delete(exam)
            return BaseResponseDto(success=result.success, code=result.code, data=result.data, message="Exam deleted successfully.")

        except Exception as ex:
            await self.logger.log("Delete", "Exam", "error", 500, "Error deleting exam", "ExamService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while deleting exam.")

    async def get_exams_admin(self, query: QueryModel[ExamSearchDto]) -> BaseResponseDto[list[Task]]:
        try:
            current_user = (await self.helper_service.get_logged_in_user()).data
            permissions = (await self.user_service.get_user_permissions()).data or []

            # Admin Faculty/Department/Year Filtering overrides
            if "Access All Faculties" not in permissions and not query.data.faculty_id:
                query.data.faculty_id = current_user.faculty_id
            if "Access All Departments" not in permissions and not query.data.department_id:
                query.data.department_id = current_user.department_id
            if "Access All Years" not in permissions and not query.data.year_id:
                query.data.year_id = current_user.year_id

            # Base condition to only get exams
            base_condition = (Task.type == "exam")

            # Date range filters
            date_conditions = []
            if query.data.start_date:
                start_date = TimezoneHandler.from_isoformat(query.data.start_date).date()
                date_conditions.append(Task.due_date >= start_date)
            if query.data.end_date:
                end_date = TimezoneHandler.from_isoformat(query.data.end_date).date()
                date_conditions.append(Task.due_date <= end_date)

            # Generate dynamic predicates based on the rest of the DTO
            dynamic_predicate = self.helper_service.generate_dynamic_predicate(
                Task, query.data, ["name"], query.is_and, query.starts_with, query.is_exact
            )

            # Combine all predicates
            all_conditions = [base_condition] + date_conditions
            if dynamic_predicate is not None:
                all_conditions.append(dynamic_predicate)
            
            final_predicate = and_(*all_conditions)

            # Resolve Dynamic Includes and Selects
            includes = self.helper_service.generate_dynamic_includes(Task, query.includes)
            selects = self.helper_service.generate_dynamic_selects("Task", query.selects)
            order_by = self.helper_service.generate_dynamic_order_by("Task", query.order_by)

            # Default ordering if none provided
            if not order_by:
                order_by = [Task.deadline]
                query.descending = False

            return await self.task_repository.find(
                predicate=final_predicate,
                includes=includes,
                selects=selects,
                order_by=order_by,
                descending=query.descending,
                page=query.page,
                limit=query.limit,
            )

        except Exception as ex:
            await self.logger.log("Get", "Exams", "error", 500, "Error fetching admin exams", "ExamService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while fetching exams.")

    async def get_exam_admin(self, exam_id: int) -> BaseResponseDto[Task]:
        try:
            includes = [
                selectinload(Task.author), selectinload(Task.subject),
                selectinload(Task.faculty), selectinload(Task.department), selectinload(Task.year)
            ]
            result = await self.task_repository.find_one(
                and_(Task.id == exam_id, Task.type == "exam"),
                includes=includes
            )
            if not result.data:
                return BaseResponseDto(success=False, code=404, message="Exam not found.")
            return result
        except Exception as ex:
            await self.logger.log("Get", "Exam", "error", 500, "Error fetching admin exam", "ExamService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while fetching the exam.")

    # ---------------------------------------------------------
    # User Specific Methods
    # ---------------------------------------------------------
    async def get_exams_user(self, query: QueryModel[ExamSearchDto]) -> BaseResponseDto[list[Task]]:
        try:
            current_user = (await self.helper_service.get_logged_in_user()).data

            # Base constraints for the student
            conditions = [
                Task.type == "exam",
                Task.faculty_id == current_user.faculty_id,
                Task.department_id == current_user.department_id,
                Task.year_id == current_user.year_id,
                # Enforces that the user is actually enrolled in the subject of the exam
                Task.subject.has(Subject.users.any(User.id == current_user.id))
            ]

            # Custom Date filters
            if query.data.start_date:
                start_date = TimezoneHandler.from_isoformat(query.data.start_date)
                conditions.append(Task.deadline >= start_date)
            if query.data.end_date:
                end_date = TimezoneHandler.from_isoformat(query.data.end_date)
                conditions.append(Task.deadline <= end_date)

            # Setup basic query predicate (Subject ID and Name filtering handled dynamically)
            dynamic_predicate = self.helper_service.generate_dynamic_predicate(
                Task, query.data, ["name"], query.is_and, query.starts_with, query.is_exact
            )
            if dynamic_predicate is not None:
                conditions.append(dynamic_predicate)

            final_predicate = and_(*conditions)

            includes = self.helper_service.generate_dynamic_includes(Task, query.includes)
            
            # Default includes for user perspective
            if not includes:
                includes = [selectinload(Task.subject), selectinload(Task.author)]

            # Default ordering
            order_by = self.helper_service.generate_dynamic_order_by("Task", query.order_by)
            if not order_by:
                order_by = [Task.deadline]
                query.descending = False

            return await self.task_repository.find(
                predicate=final_predicate,
                includes=includes,
                order_by=order_by,
                descending=query.descending,
                page=query.page,
                limit=query.limit,
            )

        except Exception as ex:
            await self.logger.log("Get", "Exams", "error", 500, "Error fetching user exams", "ExamService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while fetching your exams.")

    async def get_exam_user(self, exam_id: int) -> BaseResponseDto[Task]:
        try:
            current_user = (await self.helper_service.get_logged_in_user()).data
            
            # Enforce enrollment check within the query directly
            predicate = and_(
                Task.id == exam_id, 
                Task.type == "exam",
                Task.subject.has(Subject.users.any(User.id == current_user.id))
            )
            
            result = await self.task_repository.find_one(
                predicate=predicate,
                includes=[selectinload(Task.subject), selectinload(Task.author)]
            )
            
            if not result.data:
                return BaseResponseDto(success=False, code=404, message="Exam not found or you are not enrolled in its subject.")
                
            return result

        except Exception as ex:
            await self.logger.log("Get", "Exam", "error", 500, "Error fetching user exam", "ExamService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while fetching the exam.")