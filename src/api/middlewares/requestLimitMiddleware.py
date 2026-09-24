import os
from fastapi import HTTPException
from core.iMiddlewares.iRequestLimitMiddleware import IRequestLimitMiddleware
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.cachingHandler import caching_handler


class RequestLimitMiddleware(IRequestLimitMiddleware):
    def __init__(
        self,
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.logger = logger
        self.helper_service = helper_service
        self.request_limit_threshold = int(
            os.environ.get("REQUEST_LIMIT_THRESHOLD", "500")
        )  # Default threshold is 500 requests

    async def throttle(self, request):
        try:
            ip = request.client.host if request.client else None
            if not ip:
                return None  # Allow the request to proceed if IP is not available
            cache_key = f"request_limit:{ip}"
            requests_response = await caching_handler.get(cache_key)
            requests = []
            if requests_response:
                requests = requests_response.get("requests", [])
            i = 0
            for request in requests:
                request_time = TimezoneHandler.from_isoformat(request)
                if TimezoneHandler.add_minutes(-1) < request_time:
                    break
                i += 1
            if i < len(requests):
                requests = requests[i:]
            else:
                requests = []
            if len(requests) >= self.request_limit_threshold:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later.",
                )
            requests.append(TimezoneHandler.now().isoformat())
            await caching_handler.set(cache_key, {"requests": requests})
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
