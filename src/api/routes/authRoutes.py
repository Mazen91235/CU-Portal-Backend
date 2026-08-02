from fastapi import APIRouter, Request, Depends
from customRoute import CustomRoute
from core.iControllers.iUserController import IUserController
from core.iMiddlewares.iAuthMiddleware import IAuthMiddleware
from core.iMiddlewares.iValidationMiddleware import IValidationMiddleware
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userDtos import UserResponseDto, UserTokenDetailsResponseDto


def create_auth_router(
    controller_provider, auth_middleware_provider, validation_middleware_provider
):
    router = APIRouter(prefix="/auth", tags=["Authentication"], route_class=CustomRoute)

    def _get_controller() -> IUserController:
        return controller_provider()

    def _get_auth_middleware() -> IAuthMiddleware:
        return auth_middleware_provider()

    def _get_validation_middleware() -> IValidationMiddleware:
        return validation_middleware_provider()

    async def _is_logged_in(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
    ):
        return await auth_middleware.is_logged_in(request)

    async def _is_logged_out(
        request: Request,
        auth_middleware: IAuthMiddleware = Depends(_get_auth_middleware),
    ):
        return await auth_middleware.is_logged_out(request)

    def _validate(*keys):
        async def validate_request(
            request: Request,
            validation_middleware: IValidationMiddleware = Depends(
                _get_validation_middleware
            ),
        ):
            return await validation_middleware.validate(request, *keys)

        return validate_request

    @router.post(
        "/register",
        dependencies=[
            Depends(_is_logged_out),
            Depends(
                _validate(
                    "name",
                    "email",
                    "phone",
                    "gender",
                    "agreed",
                    "is_early_access",
                    "google_details_token",
                )
            ),
        ],
        response_model=BaseResponseDto,
        status_code=201,
        summary="Register a new user",
        description="Registers a new user with the provided details. Returns a success message upon successful registration.",
    )
    async def register(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.create(request)

    @router.post(
        "/verify-email",
        dependencies=[
            Depends(_is_logged_out),
            Depends(_validate("code")),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Verify user email",
        description="Verifies the user's email using the provided verification code. Returns a success message upon successful verification.",
    )
    async def verify_email(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.verify_email(request)

    @router.post(
        "/resend-token",
        dependencies=[
            Depends(_is_logged_out),
        ],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Resend verification token",
        description="Resends the email verification token to the user's email address.",
    )
    async def resend_token(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.resend_token(request)

    @router.get(
        "/token-details",
        dependencies=[Depends(_is_logged_out)],
        response_model=BaseResponseDto[UserTokenDetailsResponseDto],
        status_code=200,
        summary="Get token details",
        description="Retrieves details about the stored token (if any), including its stored user details and can resend after time.",
    )
    async def token_details(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.get_token_details(request)

    @router.post(
        "/google-stored-token",
        dependencies=[
            Depends(_is_logged_out),
            Depends(_validate("google_details_token", "oauth_state")),
        ],
        response_model=BaseResponseDto[str],
        status_code=200,
        summary="Get stored Google token",
        description="Retrieves a google access token for the user from the stored google details token provided from the user. Returns the token if successful.",
    )
    async def google_stored_token(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.get_google_stored_token(request)

    @router.get(
        "/google-access-token",
        dependencies=[Depends(_is_logged_in)],
        response_model=BaseResponseDto[str],
        status_code=200,
        summary="Get Google access token",
        description="Retrieves a google access token for the user from the stored google refresh token. Returns the token if successful.",
    )
    async def google_access_token(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.get_google_access_token(request)

    @router.get(
        "/is-logged-in",
        dependencies=[Depends(_is_logged_in)],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Check if user is logged in",
        description="Checks if the current user is logged in and returns a boolean value accordingly.",
    )
    async def is_logged_in(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.is_logged_in(request)

    @router.get(
        "/login-with-google",
        dependencies=[Depends(_is_logged_out)],
        summary="Login with Google",
        description="Initiates the Google login process and redirects the user to the Google authentication page.",
    )
    async def login_with_google(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.login_with_google(request)

    @router.get(
        "/google-authentication-redirect",
        dependencies=[Depends(_is_logged_out)],
        summary="Handle Google authentication redirect",
        description="Handles the redirect from Google after user authentication and processes the login. User is then redirected to the frontend url with the authentication result and token if logged in.",
    )
    async def google_authentication_redirect(
        request: Request, controller: IUserController = Depends(_get_controller)
    ):
        return await controller.google_authentication_redirect(request)

    @router.get(
        "/logout",
        dependencies=[Depends(_is_logged_in)],
        response_model=BaseResponseDto,
        status_code=200,
        summary="Logout user",
        description="Logs out the current user and returns a boolean value indicating the success of the operation.",
    )
    async def logout(
        request: Request,
        controller: IUserController = Depends(_get_controller),
    ):
        return await controller.logout(request)

    return router
