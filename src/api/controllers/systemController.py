from core.iControllers.iSystemController import ISystemController
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.responseHandler import ResponseHandler


class SystemController(ISystemController):
    def __init__(self, logger: IBaseLogger):
        self.logger = logger

    # System Specific Functions
    async def health_check(self, request):
        try:
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="System is healthy",
            )
        except Exception as e:
            await self.logger.log(
                action="HealthCheck",
                entity="System",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="SystemController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
