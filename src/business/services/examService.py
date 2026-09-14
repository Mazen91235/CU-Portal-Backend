from sqlalchemy import and_, func
from core.iServices.iExamService import IExamService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.task import Task
from core.entities.subject import Subject
from core.entities.notification import Notification
from core.dtos.baseDtos import BaseResponseDto
from core.utils.timezoneHandler import TimezoneHandler


class ExamService(IExamService):
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
                and_(predicate, Task.task_type == "exam")
                if predicate is not None
                else Task.task_type == "exam"
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

            exam = result.data

            return BaseResponseDto(success=True, code=200, data=exam)

        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Exam",
                level="error",
                code=500,
                message="Error finding exam",
                details={"error": repr(ex)},
                source="ExamService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding the exam",
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
                and_(predicate, Task.task_type == "exam")
                if predicate is not None
                else Task.task_type == "exam"
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
            exams = result.data
            return BaseResponseDto(
                success=True, code=200, data=exams, next_page=result.next_page
            )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Exam",
                level="error",
                code=500,
                message="An error occurred while finding exams",
                details={"error": repr(ex)},
                source="ExamService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding exams",
            )

    async def create(self, data):
        try:
            existing_exam_response = await self.task_repository.find_one(
                and_(
                    func.lower(Task.name) == func.lower(data.name),
                    Task.task_type == "exam",
                    Task.subject_id == data.subject_id,
                )
            )
            if not existing_exam_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_exam_response.code,
                    data=None,
                    message=existing_exam_response.message,
                )
            existing_exam = existing_exam_response.data
            if existing_exam:
                await self.logger.log(
                    action="Create",
                    entity="Exam",
                    level="warning",
                    code=400,
                    message="Exam with the same name already exists for this subject.",
                    details={"name": data.name, "subject_id": data.subject_id},
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Exam with the same name already exists for this subject.",
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
                    entity="Exam",
                    level="warning",
                    code=404,
                    message="Subject not found for exam creation",
                    details={"subject_id": data.subject_id},
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Subject not found for exam creation",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Exam Creation.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating exam",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Create",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="No logged-in user found for Exam Creation.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating exam",
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
                    entity="Exam",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user {logged_in_user.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to create exam for the specified criteria.",
                )
            data.task_type = "exam"
            create_exam_response = await self.task_repository.create(data)
            if not create_exam_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_exam_response.code,
                    data=None,
                    message=create_exam_response.message,
                )
            created_exam = create_exam_response.data
            if not created_exam:
                await self.logger.log(
                    action="Create",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="Failed to create exam without a specific error.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating exam",
                )
            share_link = f"/user/exams/{created_exam.id}"
            await self.helper_service.send_notification(
                Notification.NotificationType.EXAM,
                created_exam.id,
                f"New exam '{created_exam.name}' has been created for subject {subject.name}.",
                share_link,
                subject_id=created_exam.subject_id,
            )
            await self.logger.log(
                action="Create",
                entity="Exam",
                level="info",
                code=201,
                message="Exam created successfully",
                source="ExamService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_exam,
                message="Exam created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Exam",
                level="error",
                code=500,
                message="An error occurred while creating exam",
                details={"error": repr(ex)},
                source="ExamService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating exam",
            )

    async def update(self, data):
        try:
            target_exam_response = await self.task_repository.find_one(
                and_(Task.id == data.id, Task.task_type == "exam")
            )
            if not target_exam_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_exam_response.code,
                    data=None,
                    message=target_exam_response.message,
                )
            target_exam = target_exam_response.data
            if not target_exam:
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="info",
                    code=404,
                    message="Exam not found for update",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Exam not found",
                )
            existing_exam_response = await self.task_repository.find_one(
                and_(
                    func.lower(Task.name) == func.lower(data.name),
                    Task.task_type == "exam",
                    Task.subject_id == data.subject_id,
                )
            )
            if not existing_exam_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_exam_response.code,
                    data=None,
                    message=existing_exam_response.message,
                )
            existing_exam = existing_exam_response.data
            if existing_exam and existing_exam.id != data.id:
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="warning",
                    code=400,
                    message="Another exam with the same name already exists for this subject.",
                    details={"name": data.name, "subject_id": data.subject_id},
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Another exam with the same name already exists for this subject.",
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
                    entity="Exam",
                    level="warning",
                    code=404,
                    message="Subject not found for exam update",
                    details={"subject_id": data.subject_id},
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Subject not found for exam update",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Exam Update.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating exam",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="No logged-in user found for Exam Update.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating exam",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=data.subject_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user {logged_in_user.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to update exam for the specified criteria.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Exam Update.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating exam",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Exam Update.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating exam",
                )
            if (
                logged_in_user.id != target_exam.author_id
                and "Manage All Exams" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="warning",
                    code=403,
                    message="User does not have permission to update this exam.",
                    details={
                        "user_id": logged_in_user.id,
                        "exam_id": target_exam.id,
                    },
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to update this exam.",
                )
            data.author_id = logged_in_user.id
            data.due_date = (
                TimezoneHandler.to_date(data.deadline) if data.deadline else None
            )
            target_exam.name = data.name
            target_exam.deadline = data.deadline
            target_exam.due_date = data.due_date
            target_exam.subject_id = data.subject_id
            target_exam.details = data.details
            target_exam.author_id = data.author_id
            update_response = await self.task_repository.update(target_exam)
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_exam = update_response.data
            if not updated_exam:
                await self.logger.log(
                    action="Update",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="Failed to update exam without a specific error.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating exam",
                )
            share_link = f"/user/exams/{updated_exam.id}"
            await self.helper_service.send_notification(
                Notification.NotificationType.EXAM,
                updated_exam.id,
                f"Exam '{updated_exam.name}' has been updated for subject {subject.name}.",
                share_link,
                subject_id=updated_exam.subject_id,
            )
            await self.logger.log(
                action="Update",
                entity="Exam",
                level="info",
                code=200,
                message="Exam updated successfully",
                source="ExamService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_exam,
                message="Exam updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Exam",
                level="error",
                code=500,
                message="An error occurred while updating exam",
                details={"error": repr(ex)},
                source="ExamService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating exam",
            )

    async def delete(self, data):
        try:
            target_exam_response = await self.task_repository.find_one(
                and_(Task.id == data.id, Task.task_type == "exam")
            )
            if not target_exam_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_exam_response.code,
                    data=None,
                    message=target_exam_response.message,
                )
            target_exam = target_exam_response.data
            if not target_exam:
                await self.logger.log(
                    action="Delete",
                    entity="Exam",
                    level="warning",
                    code=404,
                    message="Exam not found for deletion",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Exam not found",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Exam Deletion.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting exam",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Delete",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="No logged-in user found for Exam Deletion.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting exam",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=data.subject_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Exam",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user {logged_in_user.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to delete exam for the specified criteria.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Exam Delete.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting exam",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Delete",
                    entity="Exam",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Exam Delete.",
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting exam",
                )
            if (
                logged_in_user.id != target_exam.author_id
                and "Manage All Exams" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Delete",
                    entity="Exam",
                    level="warning",
                    code=403,
                    message="User does not have permission to delete this exam.",
                    details={
                        "user_id": logged_in_user.id,
                        "exam_id": target_exam.id,
                    },
                    source="ExamService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to delete this exam.",
                )
            delete_response = await self.task_repository.delete(target_exam)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            await self.logger.log(
                action="Delete",
                entity="Exam",
                level="info",
                code=200,
                message="Exam deleted successfully",
                source="ExamService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Exam deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Exam",
                level="error",
                code=500,
                message="An error occurred while deleting exam",
                details={"error": repr(ex)},
                source="ExamService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting exam",
            )
