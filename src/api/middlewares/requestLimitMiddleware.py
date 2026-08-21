import os
from fastapi import HTTPException
from core.iMiddlewares.iRequestLimitMiddleware import IRequestLimitMiddleware
from core.iServices.iRequestLimitService import IRequestLimitService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.dtos.requestLimitDtos import RequestLimitSearchDto


class RequestLimitMiddleware(IRequestLimitMiddleware):
    def __init__(
        self,
        request_limit_service: IRequestLimitService,
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.request_limit_service = request_limit_service
        self.logger = logger
        self.helper_service = helper_service
        self.request_limit_threshold = os.environ.get(
            "REQUEST_LIMIT_THRESHOLD", 500
        )  # Default threshold is 500 requests

    async def throttle(self, request):
        try:
            ip = request.client.host if request.client else None
            route = request.url.path if request.url else None
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if logged_in_user_response.success and logged_in_user_response.data:
                logged_in_user = logged_in_user_response.data
                user_id = logged_in_user.id
            else:
                user_id = None
            request_limit_search_dto = RequestLimitSearchDto(
                ip=ip,
                route=route,
                user_id=user_id,
            )
            request_limit_count_response = await self.request_limit_service.count(
                request_limit_search_dto,
                is_and=True,
            )
            if not request_limit_count_response.success:
                raise HTTPException(
                    status_code=request_limit_count_response.code or 500,
                    detail=request_limit_count_response.message,
                )
            request_limit_count = request_limit_count_response.data or 0
            if request_limit_count >= int(self.request_limit_threshold):
                await self.logger.log(
                    action="Throttle",
                    entity="Request",
                    level="warning",
                    code=429,
                    message=f"Request limit exceeded for IP: {ip}, Route: {route}, User ID: {user_id}",
                    source="RequestLimitMiddleware",
                )
                raise HTTPException(
                    status_code=429,
                    detail="Too Many Requests: Request limit exceeded. Please try again later.",
                )
            create_request_limit_response = await self.request_limit_service.create(
                ip, route, user_id
            )
            if not create_request_limit_response.success:
                raise HTTPException(
                    status_code=create_request_limit_response.code or 500,
                    detail=create_request_limit_response.message,
                )
            return None  # Allow the request to proceed if under the limit
        except HTTPException as http_ex:
            raise http_ex
        except Exception as ex:
            await self.logger.log(
                action="ThrottleError",
                entity="Request",
                level="error",
                code=500,
                message="An error occurred during request throttling.",
                details={"error": repr(ex)},
                source="RequestLimitMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="An error occurred during request throttling. Please try again later.",
            )
