import os
from fastapi import Request, Response
from fastapi.security import APIKeyCookie
from typing import Literal

cookie_scheme = APIKeyCookie(name="token", auto_error=False)


class CookieHandler:
    @staticmethod
    def get_cookie(request: Request, key: str):
        return request.cookies.get(key)

    @staticmethod
    def set_cookie(
        response: Response,
        key: str,
        value: str | None,
        max_age: int = 0,
        expires: int = 0,
        path: str = "/",
        domain: str | None = None,
        secure: bool = True,
        httponly: bool = True,
        samesite: Literal["lax"] = "lax",
    ):
        if not value:
            response.delete_cookie(key=key, path=path, domain=domain)
            return

        testing = os.environ.get("TESTING", "false").lower() == "true"
        effective_secure = secure and not testing

        response.set_cookie(
            key=key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=effective_secure,
            httponly=httponly,
            samesite=samesite,
        )

    @staticmethod
    def delete_cookie(response: Response, key: str):
        response.delete_cookie(key=key)
