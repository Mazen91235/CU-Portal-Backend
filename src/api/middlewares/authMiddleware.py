from fastapi import Request, HTTPException
from datetime import timedelta
from sqlalchemy import and_
from business.contextVars.userContext import user_context
from business.contextVars.patientContext import patient_context
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.user import User
from core.entities.patient import Patient
from core.entities.token import Token
from core.utils.timezoneHandler import TimezoneHandler
from core.iLoggers.iBaseLogger import IBaseLogger


class AuthMiddleware(IAuthMiddleware):
    def __init__(
        self,
        user_repository: IBaseRepository[User],
        patient_repository: IBaseRepository[Patient],
        token_repository: IBaseRepository[Token],
        logger: IBaseLogger,
    ):
        self.user_repository = user_repository
        self.patient_repository = patient_repository
        self.token_repository = token_repository
        self.logger = logger

    async def is_logged_in(self, request: Request):
        try:
            cookies = request.cookies
            refresh_token = cookies.get("token")
            if not refresh_token:
                await self.logger.log(
                    action="AuthCheck",
                    entity="User",
                    level="warning",
                    code=401,
                    message="No refresh token provided in request cookies",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: No refresh token provided",
                )

            token_response = await self.token_repository.find_one(
                and_(
                    Token.token == refresh_token,
                    Token.type == Token.TokenType.REFRESH_TOKEN,
                    Token.expires_at > TimezoneHandler.now("UTC"),
                )
            )

            if not token_response.success:
                raise HTTPException(
                    status_code=token_response.code, detail=token_response.message
                )
            token = token_response.data
            if not token:
                await self.logger.log(
                    action="AuthCheck",
                    entity="User",
                    level="warning",
                    code=401,
                    message="Invalid or expired refresh token provided",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Invalid or expired refresh token",
                )

            user_response = await self.user_repository.find_one(
                User.id == token.user_id
            )

            if not user_response.success:
                raise HTTPException(
                    status_code=user_response.code, detail=user_response.message
                )
            user = user_response.data
            if not user:
                await self.logger.log(
                    action="AuthCheck",
                    entity="User",
                    level="warning",
                    code=401,
                    message="User associated with refresh token not found",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: User not found for provided token",
                )

            user_context.set(user)

            if token.expires_at - TimezoneHandler.now("UTC") < timedelta(
                days=User.RefreshToken.MINIMUM_DAYS
            ):
                token.expires_at = TimezoneHandler.now("UTC") + timedelta(
                    days=User.RefreshToken.EXPIRE_DAYS
                )
                update_token_response = await self.token_repository.update(
                    token, ["expires_at"]
                )
                if not update_token_response.success:
                    raise HTTPException(
                        status_code=update_token_response.code,
                        detail=update_token_response.message,
                    )
                await self.logger.log(
                    action="RefreshToken",
                    entity="User",
                    level="info",
                    code=200,
                    message="Refresh token expiration extended for user",
                    source="AuthMiddleware",
                )

            # Since this is a dependency, returning without an error allows the request to proceed.
            # You can optionally return the user object here if you want routes to access it via dependency injection.
            return user

        except HTTPException:
            # Let expected HTTP exceptions pass through to the client
            raise
        except Exception as ex:
            await self.logger.log(
                action="AuthCheck",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred during authentication check: {str(ex)}",
                source="AuthMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error during authentication check",
            )

    async def is_logged_out(self, request: Request):
        try:
            cookies = request.cookies
            refresh_token = cookies.get("token")
            if refresh_token:
                token_response = await self.token_repository.find_one(
                    and_(
                        Token.token == refresh_token,
                        Token.type == Token.TokenType.REFRESH_TOKEN,
                        Token.expires_at > TimezoneHandler.now("UTC"),
                    )
                )
                if not token_response.success:
                    raise HTTPException(
                        status_code=token_response.code,
                        detail=token_response.message,
                    )

                if token_response.data:
                    token = token_response.data
                    user_response = await self.user_repository.find_one(
                        User.id == token.user_id
                    )
                    if not user_response.success:
                        raise HTTPException(
                            status_code=user_response.code,
                            detail=user_response.message,
                        )
                    user = user_response.data
                    if user:
                        raise HTTPException(
                            status_code=400,
                            detail="Bad Request: User is already logged in",
                        )

            # Dependency passes successfully
            return None

        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="AuthCheck",
                entity="User",
                level="error",
                code=500,
                message=f"An error occurred during authentication check: {str(ex)}",
                source="AuthMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error during authentication check",
            )

    async def is_logged_in_patient(self, request: Request):
        try:
            headers = request.headers
            refresh_token = headers.get("Authorization")
            if not refresh_token or not refresh_token.startswith("Bearer "):
                await self.logger.log(
                    action="AuthCheck",
                    entity="Patient",
                    level="warning",
                    code=401,
                    message="No refresh token provided in request headers",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: No refresh token provided",
                )

            refresh_token = refresh_token.split(" ")[1]
            patient_response = await self.patient_repository.find_one(
                Patient.refresh_token == refresh_token
            )

            if not patient_response.success:
                raise HTTPException(
                    status_code=patient_response.code,
                    detail=patient_response.message,
                )

            patient = patient_response.data
            if not patient:
                await self.logger.log(
                    action="AuthCheck",
                    entity="Patient",
                    level="warning",
                    code=401,
                    message="Patient associated with refresh token not found",
                    source="AuthMiddleware",
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Patient not found for provided token",
                )

            patient_context.set(patient)

            # Since this is a dependency, returning without an error allows the request to proceed.
            # You can optionally return the patient object here if you want routes to access it via dependency injection.
            return patient

        except HTTPException:
            # Let expected HTTP exceptions pass through to the client
            raise
        except Exception as ex:
            await self.logger.log(
                action="AuthCheck",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred during authentication check: {str(ex)}",
                source="AuthMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error during authentication check",
            )

    async def is_logged_out_patient(self, request: Request):
        try:
            headers = request.headers
            refresh_token = headers.get("Authorization")
            if refresh_token and refresh_token.startswith("Bearer "):
                refresh_token = refresh_token.split(" ")[1]
                patient_response = await self.patient_repository.find_one(
                    Patient.refresh_token == refresh_token
                )
                if not patient_response.success:
                    raise HTTPException(
                        status_code=patient_response.code,
                        detail=patient_response.message,
                    )
                patient = patient_response.data
                if patient:
                    raise HTTPException(
                        status_code=400,
                        detail="Bad Request: Patient is already logged in",
                    )

            # Dependency passes successfully
            return None

        except HTTPException:
            raise
        except Exception as ex:
            await self.logger.log(
                action="AuthCheck",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred during authentication check: {str(ex)}",
                source="AuthMiddleware",
            )
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error during authentication check",
            )
