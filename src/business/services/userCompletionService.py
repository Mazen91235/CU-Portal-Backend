from sqlalchemy import and_
from core.iServices.iUserCompletionService import IUserCompletionService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.userCompletion import UserCompletion
from core.entities.weekItem import WeekItem
from core.entities.task import Task
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userCompletionDtos import UserCompletionSearchDto


class UserCompletionService(IUserCompletionService):
    def __init__(
        self,
        user_completion_repository: IBaseRepository[UserCompletion],
        week_item_repository: IBaseRepository[WeekItem],
        task_repository: IBaseRepository[Task],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.user_completion_repository = user_completion_repository
        self.week_item_repository = week_item_repository
        self.task_repository = task_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.user_completion_repository.begin_transaction()

    async def commit_transaction(self):
        await self.user_completion_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.user_completion_repository.rollback_transaction()

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
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="FindOne",
                    entity="UserCompletion",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged-in user for user completion retrieval",
                    details={"error": logged_in_user_response.message},
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="FindOne",
                    entity="UserCompletion",
                    level="error",
                    code=401,
                    message="No logged-in user found for user completion retrieval",
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="User is not logged in",
                )
            data = data or UserCompletionSearchDto()
            data.user_id = logged_in_user.id
            predicate = self.helper_service.generate_dynamic_predicate(
                UserCompletion,
                data,
                [],
                True,
                starts_with,
                is_exact,
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                UserCompletion, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "UserCompletion", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "UserCompletion", order_by, descending
            )
            result = await self.user_completion_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            return BaseResponseDto(success=True, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="UserCompletion",
                level="error",
                code=500,
                message="An error occurred while finding user completion",
                details={"error": repr(ex)},
                source="UserCompletionService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding user completion",
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
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Find",
                    entity="UserCompletion",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged-in user for user completion retrieval",
                    details={"error": logged_in_user_response.message},
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Find",
                    entity="UserCompletion",
                    level="error",
                    code=401,
                    message="No logged-in user found for user completion retrieval",
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="User is not logged in",
                )
            data = data or UserCompletionSearchDto()
            data.user_id = logged_in_user.id
            predicate = self.helper_service.generate_dynamic_predicate(
                UserCompletion,
                data,
                [],
                True,
                starts_with,
                is_exact,
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                UserCompletion, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "UserCompletion", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "UserCompletion", order_by, descending
            )
            result = await self.user_completion_repository.find(
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
            return BaseResponseDto(
                success=True, data=result.data, next_page=result.next_page
            )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="UserCompletion",
                level="error",
                code=500,
                message="An error occurred while finding user completions",
                details={"error": repr(ex)},
                source="UserCompletionService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding user completions",
            )

    async def create(self, data):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Create",
                    entity="UserCompletion",
                    level="error",
                    code=401,
                    message="Failed to retrieve logged-in user for user completion creation",
                    details={"error": logged_in_user_response.message},
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code or 401,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Create",
                    entity="UserCompletion",
                    level="error",
                    code=401,
                    message="No logged-in user found for user completion creation",
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="User is not logged in",
                )

            if data.week_item_id is None and data.task_id is None:
                await self.logger.log(
                    action="Create",
                    entity="UserCompletion",
                    level="warning",
                    code=400,
                    message="At least one completion target is required",
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Either week_item_id or task_id is required",
                )

            if data.week_item_id is not None and data.task_id is not None:
                await self.logger.log(
                    action="Create",
                    entity="UserCompletion",
                    level="warning",
                    code=400,
                    message="Only one completion target can be provided",
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Only one of week_item_id or task_id can be provided",
                )

            if data.week_item_id is not None:
                week_item_response = await self.week_item_repository.find_one(
                    WeekItem.id == data.week_item_id
                )
                if not week_item_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=week_item_response.code,
                        data=None,
                        message=week_item_response.message,
                    )
                week_item = week_item_response.data
                if not week_item:
                    await self.logger.log(
                        action="Create",
                        entity="UserCompletion",
                        level="warning",
                        code=404,
                        message="Week item not found for completion",
                        details={"week_item_id": data.week_item_id},
                        source="UserCompletionService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Week item not found",
                    )
                duplicate_predicate = and_(
                    UserCompletion.user_id == logged_in_user.id,
                    UserCompletion.week_item_id == data.week_item_id,
                )
            else:
                task_response = await self.task_repository.find_one(
                    Task.id == data.task_id
                )
                if not task_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=task_response.code,
                        data=None,
                        message=task_response.message,
                    )
                task = task_response.data
                if not task:
                    await self.logger.log(
                        action="Create",
                        entity="UserCompletion",
                        level="warning",
                        code=404,
                        message="Task not found for completion",
                        details={"task_id": data.task_id},
                        source="UserCompletionService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Task not found",
                    )
                duplicate_predicate = and_(
                    UserCompletion.user_id == logged_in_user.id,
                    UserCompletion.task_id == data.task_id,
                )

            existing_completion_response = (
                await self.user_completion_repository.find_one(duplicate_predicate)
            )
            if not existing_completion_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_completion_response.code,
                    data=None,
                    message=existing_completion_response.message,
                )
            existing_completion = existing_completion_response.data
            if existing_completion:
                await self.logger.log(
                    action="Create",
                    entity="UserCompletion",
                    level="warning",
                    code=400,
                    message="User completion already exists for this target",
                    details={
                        "user_id": logged_in_user.id,
                        "week_item_id": data.week_item_id,
                        "task_id": data.task_id,
                    },
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="User completion already exists",
                )

            data.user_id = logged_in_user.id
            create_response = await self.user_completion_repository.create(data)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            created_completion = create_response.data
            if not created_completion:
                await self.logger.log(
                    action="Create",
                    entity="UserCompletion",
                    level="error",
                    code=500,
                    message="Failed to create user completion",
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to create user completion",
                )
            await self.logger.log(
                action="Create",
                entity="UserCompletion",
                level="info",
                code=201,
                message="User completion created successfully",
                details={"user_completion_id": created_completion.id},
                source="UserCompletionService",
            )
            return BaseResponseDto(success=True, code=201, data=created_completion)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="UserCompletion",
                level="error",
                code=500,
                message="An error occurred while creating user completion",
                details={"error": repr(ex)},
                source="UserCompletionService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating user completion",
            )

    async def delete(self, data):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="UserCompletion",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message="Failed to retrieve logged-in user for user completion deletion",
                    details={"error": logged_in_user_response.message},
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Delete",
                    entity="UserCompletion",
                    level="error",
                    code=401,
                    message="No logged-in user found for user completion deletion",
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="User is not logged in",
                )

            completion_response = await self.user_completion_repository.find_one(
                UserCompletion.id == data.id
            )
            if not completion_response.success:
                return BaseResponseDto(
                    success=False,
                    code=completion_response.code,
                    data=None,
                    message=completion_response.message,
                )
            completion = completion_response.data
            if not completion:
                await self.logger.log(
                    action="Delete",
                    entity="UserCompletion",
                    level="warning",
                    code=404,
                    message="User completion not found for deletion",
                    details={"user_completion_id": data.id},
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="User completion not found",
                )

            if completion.user_id != logged_in_user.id:
                await self.logger.log(
                    action="Delete",
                    entity="UserCompletion",
                    level="warning",
                    code=403,
                    message="Logged in user does not own this user completion",
                    details={
                        "user_completion_id": completion.id,
                        "completion_user_id": completion.user_id,
                        "logged_in_user_id": logged_in_user.id,
                    },
                    source="UserCompletionService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You do not have permission to delete this completion",
                )

            delete_response = await self.user_completion_repository.delete(completion)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            await self.logger.log(
                action="Delete",
                entity="UserCompletion",
                level="info",
                code=200,
                message="User completion deleted successfully",
                details={"user_completion_id": completion.id},
                source="UserCompletionService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="User completion deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="UserCompletion",
                level="error",
                code=500,
                message="An error occurred while deleting user completion",
                details={"error": repr(ex)},
                source="UserCompletionService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting user completion",
            )
