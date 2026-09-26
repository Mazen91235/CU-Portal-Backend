import os
from typing import Any
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.config import Config
from authlib.integrations.starlette_client import OAuth

config = Config(".env")  # read config from .env file
oauth = OAuth(config)
google = oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    authorize_params={
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    },
    client_kwargs={
        "scope": "openid email profile https://www.googleapis.com/auth/drive.file "
    },
)


class OAuthHandler:
    @staticmethod
    def create_google_client():
        return oauth.create_client("google")

    @staticmethod
    def get_google_callback_url(request: Request) -> str:
        is_localhost = "localhost" in (request.url.hostname or "")
        return (
            ("https://" if not is_localhost else "http://")
            + (request.url.hostname or "")
            + (f":{request.url.port}" if request.url.port else "")
            + "/auth/google-authentication-redirect"
        )

    @staticmethod
    async def authorize_google_access_token(request: Request, nonce: Any):
        code = request.query_params.get("code")
        if not code:
            raise ValueError("Missing Google authorization code")

        google_client = oauth.create_client("google")
        token = await google_client.fetch_access_token(
            code=code,
            redirect_uri=OAuthHandler.get_google_callback_url(request),
        )

        if "id_token" in token:
            token["userinfo"] = await google_client.parse_id_token(
                token,
                nonce=nonce,
            )
        else:
            token["userinfo"] = await google_client.userinfo(token=token)

        return token

    @staticmethod
    async def authorize_google_redirect(
        request: Request, redirect_url: str, state: str, nonce: str
    ):
        google_client = oauth.create_client("google")
        authorization_data = await google_client.create_authorization_url(
            redirect_url,
            state=state,
            nonce=nonce,
        )
        return RedirectResponse(
            url=(
                authorization_data["url"]
                if isinstance(authorization_data, dict)
                else authorization_data
            ),
            status_code=302,
        )
