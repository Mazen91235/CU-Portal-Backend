import os
from typing import Any
from fastapi import Request
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
    async def authorize_google_access_token(request: Request, nonce: Any):
        return await oauth.google.authorize_access_token(request, nonce=nonce)

    @staticmethod
    async def authorize_google_redirect(
        request: Request, redirect_url: str, state: str, nonce: str
    ):
        return await oauth.google.authorize_redirect(
            request, redirect_url, state=state, nonce=nonce
        )
