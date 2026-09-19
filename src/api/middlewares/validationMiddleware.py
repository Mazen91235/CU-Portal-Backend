import os
from fastapi import HTTPException
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.validator import Validator


class ValidationMiddleware(IValidationMiddleware):
    def __init__(self, logger: IBaseLogger):
        self.logger = logger

    async def validate(self, request, *keys):
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
                action="Validate",
                entity="Request",
                level="error",
                code=400,
                message="An error occurred during request validation.",
                details={"error": repr(ex)},
                source="ValidationMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="An error occurred during request validation. Please try again later.",
            )

    async def validate_details_numbers(self, request, *keys):
        try:
            data = await request.json()
            details = data.get("details", {})
            for key in keys:
                if key in details and not Validator.is_number(details[key]):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid value for {key}: must be a number",
                    )
            return
        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="ValidateDetailsNumbers",
                entity="Request",
                level="error",
                code=400,
                message="An error occurred during request validation.",
                details={"error": repr(ex)},
                source="ValidationMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="An error occurred during request validation. Please try again later.",
            )

    async def validate_api_key(self, request):
        try:
            api_key = request.headers.get("X-API-Key")
            if not api_key or api_key != os.environ.get("API_KEY"):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or missing API key.",
                )
            return
        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="ValidateAPIKey",
                entity="Request",
                level="error",
                code=400,
                message="An error occurred during API key validation.",
                details={"error": repr(ex)},
                source="ValidationMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="An error occurred during API key validation. Please try again later.",
            )
