from fastapi import HTTPException
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.iLoggers.iBaseLogger import IBaseLogger


class ValidationMiddleware(IValidationMiddleware):
    def __init__(self, logger: IBaseLogger):
        self.logger = logger

    async def handle(self, request, *keys):
        try:
            data = await request.json()
            for key in keys:
                if (
                    key not in data
                    or data[key] is None
                    or (isinstance(data[key], str) and not data[key].strip())
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required field: {key}",
                    )
            return
        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="ValidationError",
                entity="Request",
                level="error",
                code=400,
                message="An error occurred during request validation.",
                details={"error": str(ex)},
                source="ValidationMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="An error occurred during request validation. Please try again later.",
            )
