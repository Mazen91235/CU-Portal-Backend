from core.iControllers.iUserCompletionController import IUserCompletionController
from core.iServices.iUserCompletionService import IUserCompletionService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.userCompletion import UserCompletion
from core.dtos.userCompletionDtos import (
    UserCompletionCreateDto,
    UserCompletionResponseDto,
    UserCompletionSearchDto,
)


class UserCompletionController(IUserCompletionController):
    def __init__(
        self, user_completion_service: IUserCompletionService, logger: IBaseLogger
    ):
        self.user_completion_service = user_completion_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[UserCompletionSearchDto].generate(
                UserCompletionSearchDto, {"id": id}
            )
            response = await self.user_completion_service.find_one(
                entity_search_dto,
                ["week_item", "task"],
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            completion = response.data
            if not completion:
                await self.logger.log(
                    action="FindOne",
                    entity="UserCompletion",
                    level="info",
                    code=404,
                    message="User completion not found",
                    source="UserCompletionController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="User completion not found",
                )
            completion_mapped = Mapper[UserCompletion, UserCompletionResponseDto].map(
                completion, UserCompletionResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=completion_mapped,
            )
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="UserCompletion",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(ex)},
                source="UserCompletionController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[UserCompletionSearchDto].generate_from_query(
                UserCompletionSearchDto, query
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

            response = await self.user_completion_service.find(
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
            completions = response.data
            completions_mapped = Mapper[
                UserCompletion, UserCompletionResponseDto
            ].map_list(completions or [], UserCompletionResponseDto, True)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=completions_mapped,
                next_page=response.next_page,
            )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="UserCompletion",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(ex)},
                source="UserCompletionController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            completion = Mapper[UserCompletionCreateDto, UserCompletion].map(
                data, UserCompletion
            )
            response = await self.user_completion_service.create(completion)
            if not response.success:
                await self.user_completion_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            completion = response.data
            if not completion:
                await self.user_completion_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="UserCompletion",
                    level="error",
                    code=500,
                    message="Failed to create user completion",
                    source="UserCompletionController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create user completion",
                )
            completion_mapped = Mapper[UserCompletion, UserCompletionResponseDto].map(
                completion, UserCompletionResponseDto, True
            )
            await self.user_completion_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=completion_mapped,
                message="User completion created successfully",
            )
        except Exception as ex:
            await self.user_completion_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="UserCompletion",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(ex)},
                source="UserCompletionController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            completion = Generator[UserCompletion].generate(
                UserCompletion, {"id": id}
            )
            response = await self.user_completion_service.delete(completion)
            if not response.success:
                await self.user_completion_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.user_completion_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="User completion deleted successfully",
            )
        except Exception as ex:
            await self.user_completion_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="UserCompletion",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(ex)},
                source="UserCompletionController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
