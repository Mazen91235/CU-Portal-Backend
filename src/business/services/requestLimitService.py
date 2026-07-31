from core.iServices.iRequestLimitService import IRequestLimitService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.requestLimit import RequestLimit
from core.dtos.baseDtos import BaseResponseDto


class RequestLimitService(IRequestLimitService):
    def __init__(
        self,
        request_limit_repository: IBaseRepository[RequestLimit],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.request_limit_repository = request_limit_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.request_limit_repository.begin_transaction()

    async def commit_transaction(self):
        await self.request_limit_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.request_limit_repository.rollback_transaction()

    # CRUD Functions
    async def count(
        self,
        data=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                RequestLimit, data, [], is_and, starts_with, is_exact
            )
            result = await self.request_limit_repository.count(
                predicate,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            request_limit_count = result.data
            return BaseResponseDto(success=True, data=request_limit_count)
        except Exception as ex:
            await self.logger.log(
                action="Count",
                entity="RequestLimit",
                level="error",
                code=500,
                message=f"An error occurred while counting request limits",
                details={"error": str(ex)},
                source="RequestLimitService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while counting request limits",
            )

    async def create(self, ip, route, user_id):
        try:
            data = RequestLimit(
                ip=ip,
                route=route,
                status=True,  # Dummy
                user_id=user_id,
            )
            create_request_limit_response = await self.request_limit_repository.create(
                data
            )
            if not create_request_limit_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_request_limit_response.code,
                    data=None,
                    message=create_request_limit_response.message,
                )
            return BaseResponseDto(success=True, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="RequestLimit",
                level="error",
                code=500,
                message=f"An error occurred while creating a request limit",
                details={"error": str(ex)},
                source="RequestLimitService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating a request limit",
            )
